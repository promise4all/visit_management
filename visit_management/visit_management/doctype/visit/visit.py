from __future__ import annotations

import frappe
from frappe import whitelist, _
from frappe.model.document import Document
from frappe.utils import now_datetime
from visit_management.visit_management.settings_utils import (
	is_photo_required,
	require_geolocation_on_completion,
	is_checkin_mandatory_for_user,
)


class Visit(Document):
	@classmethod
	def default_list_data(cls):
		"""Provide list metadata for CRM ViewControls.

		Matches the fields returned by the frontend list resource to avoid AttributeError
		in crm.api.doc.get_data.
		"""
		return {
			"columns": [
				{"label": _("Visit"), "fieldname": "name", "fieldtype": "Link", "options": "Visit"},
				{"label": _("Client Type"), "fieldname": "client_type", "fieldtype": "Data"},
				{"label": _("Client"), "fieldname": "client", "fieldtype": "Dynamic Link", "options": "client_type"},
				{"label": _("Status"), "fieldname": "status", "fieldtype": "Data"},
				{"label": _("Scheduled Time"), "fieldname": "scheduled_time", "fieldtype": "Datetime"},
			],
			"filters": [],
		}
	def _sync_photo_field(self, fieldname: str):
		"""Ensure the photo field is populated from existing File attachments if present."""
		if self.get(fieldname):
			return
		# Prefer files explicitly linked to the field, but fall back to any file on the doc
		for filters in (
			{"attached_to_doctype": self.doctype, "attached_to_name": self.name, "attached_to_field": fieldname},
			{"attached_to_doctype": self.doctype, "attached_to_name": self.name, "attached_to_field": ["is", "not set"]},
		):
			existing = frappe.get_all(
				"File",
				filters=filters,
				order_by="creation desc",
				pluck="file_url",
				limit=1,
			)
			if existing:
				self.set(fieldname, existing[0])
				break
	def _normalize_geolocation(self):
		"""Ensure geolocation field is stored as JSON string not a raw dict to avoid pymysql TypeError.

		Frappe's DB layer expects scalar types; a Python dict leaks through if client passes object literal.
		If value is already a string, leave as-is. If dict with lat/lng keys, serialize via frappe.as_json.
		"""
		try:
			val = self.get("location")
			if isinstance(val, dict):
				# minimal sanitization: keep only lat/lng if present
				payload = {}
				for k in ("lat", "lng"):
					if k in val:
						payload[k] = val[k]
				if payload:
					self.set("location", frappe.as_json(payload))
				else:
					# empty dict -> clear
					self.set("location", None)
		except Exception:
			pass

	def before_insert(self):
		self._normalize_geolocation()

	def before_save(self):
		self._normalize_geolocation()
		
		# Auto-submit when status is Completed
		if self.status == "Completed" and self.docstatus == 0 and not self.flags.get('in_submit'):
			self.flags.in_submit = True
			# We'll submit after save in on_update

	def before_submit(self):
		"""Validate that submission is only allowed when status is Completed."""
		if self.status != "Completed":
			frappe.throw(_("Visit can only be submitted when status is Completed."))

	def on_update(self):
		"""Auto-submit the document when status is set to Completed."""
		if self.status == "Completed" and self.docstatus == 0 and self.flags.get('in_submit'):
			self.flags.in_submit = False
			# Allow auto-submit even if user lacks submit permission; business logic controls when this happens.
			self.flags.ignore_permissions = True
			self.submit()
	
	def on_cancel(self):
		"""Handle visit cancellation."""
		# Set status to Cancelled when document is cancelled
		self.db_set('status', 'Cancelled', update_modified=False)
	
	def on_trash(self):
		"""Prevent deletion of submitted visits."""
		if self.docstatus == 1:
			frappe.throw("Cannot delete a submitted visit. Please cancel it first.")
	
	def get_contact_options(self):
		"""Return contacts filtered by client_type and client for autocomplete"""
		client_type = self.get("client_type")
		client = self.get("client")
		
		if not client_type or not client:
			return []
		
		# Use Dynamic Link for all client types
		query = """
			SELECT DISTINCT 
				c.name, 
				c.first_name, 
				c.last_name
			FROM `tabContact` c
			WHERE EXISTS (
				SELECT 1 FROM `tabDynamic Link` dl 
				WHERE dl.parent = c.name 
					AND dl.parenttype = 'Contact'
					AND dl.link_doctype = %(client_type)s
					AND dl.link_name = %(client)s
			)
			ORDER BY c.first_name, c.last_name
		"""
		
		params = {
			"client": client,
			"client_type": client_type,
		}
		
		results = frappe.db.sql(query, params, as_dict=True)
		return [{"label": r.get("first_name", "") + " " + r.get("last_name", ""), "value": r.name} for r in results]
	def _auto_create_maintenance_visit_if_needed(self):
		"""Create a Maintenance Visit if this Visit is for a Customer, purpose is Maintenance,
		status is Completed, and no Maintenance Visit is linked yet.

		Uses minimal required fields so the record can be saved and refined later.
		"""
		try:
			purpose = (self.get("subject") or "").strip().lower()
			if not (
				purpose == "maintenance"
				and self.get("client_type") == "Customer"
				and self.get("status") == "Completed"
				and not self.get("maintenance_visit")
			):
				return None

			# Resolve company
			company = None
			try:
				company = frappe.db.get_single_value("Global Defaults", "default_company")
			except Exception:
				company = None
			if not company:
				# try first enabled company
				rows = frappe.get_all("Company", filters={"enabled": 1}, fields=["name"], limit=1)
				if rows:
					company = rows[0]["name"]

			# Maintenance date
			from frappe.utils import getdate, nowdate

			if self.get("check_out_time"):
				mdate = getdate(self.get("check_out_time"))
			elif self.get("scheduled_time"):
				mdate = getdate(self.get("scheduled_time"))
			else:
				mdate = getdate(nowdate())

			doc = frappe.get_doc({
				"doctype": "Maintenance Visit",
				"customer": self.get("client"),
				"company": company or None,
				"mntc_date": mdate,
				"maintenance_type": "Unscheduled",
				"completion_status": "Fully Completed",
			})

			# Optional mappings
			if self.get("address"):
				doc.customer_address = self.get("address")

			# Map Visit draft maintenance fields into MV Purposes row, if available
			try:
				mv_item = self.get("mv_item")
				mv_serial_no = self.get("mv_serial_no")
				mv_problem = self.get("mv_problem_reported")
				mv_work_done = self.get("mv_work_done")

				# Resolve a service person (Sales Person) - prefer one linked to assigned employee, else fallback
				service_person = self._resolve_service_person()

				if mv_item or mv_serial_no or mv_problem or mv_work_done or service_person:
					doc.append(
						"purposes",
						{
							"item_code": mv_item or None,
							"serial_no": mv_serial_no or None,
							# ERPNext MV Purpose doesn't have 'problem_reported'; use description
							"description": (mv_problem or "")[:1000] or None,
							"work_done": (mv_work_done or "")[:1000] or None,
							"service_person": service_person,
						},
					)
			except Exception:
				# Best-effort mapping; ignore if structure differs
				pass

			# Persist
			doc.insert(ignore_permissions=True)
			self.set("maintenance_visit", doc.name)
			return doc.name
		except Exception:
			return None

	def _resolve_service_person(self) -> str | None:
		"""Best-effort resolution of a Sales Person to set as service_person on MV Purpose.

		Strategy:
		- If assigned user has an Employee mapped to a Sales Person (by employee link), use it
		- Else use root 'Sales Team' if exists
		- Else return the first available Sales Person
		- Else return None
		"""
		try:
			user = self.assigned_to or frappe.session.user
			emp = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)
			sales_person = None
			if emp:
				# Try find Sales Person linked to this employee via 'employee' link field if present
				if frappe.db.exists("DocField", {"parent": "Sales Person", "fieldname": "employee"}):
					sp = frappe.db.get_value("Sales Person", {"employee": emp.name}, "name")
					if sp:
						sales_person = sp
			if not sales_person:
				# Fallback to root Sales Team if present
				if frappe.db.exists("Sales Person", "Sales Team"):
					sales_person = "Sales Team"
			if not sales_person:
				# Any available sales person
				row = frappe.get_all("Sales Person", fields=["name"], limit=1)
				if row:
					sales_person = row[0]["name"]
			return sales_person
		except Exception:
			return None

	def validate(self):
		# Skip validations when cancelling
		if self.docstatus == 1 and self.flags.get('ignore_validate_update_after_submit'):
			return
			
		# Restrict header field modifications when status is not Planned (unless cancelling)
		if self.status != "Planned" and not self.is_new() and self.docstatus != 2:
			old_doc = self.get_doc_before_save()
			if old_doc:
				# Define header fields that cannot be modified after status changes from Planned
				# Note: scheduled_time is allowed to be adjusted even after visit starts
				header_fields = {
					'assigned_to', 'client_type', 'client',
					'contact', 'subject', 'address', 'visit_brief'
				}
				changed_fields = {field for field in header_fields 
								  if self.get(field) != old_doc.get(field)}
				
				if changed_fields:
					frappe.throw(f"Cannot modify header fields ({', '.join(changed_fields)}) when visit status is not 'Planned'.")
		
		# No approval on Visit; approval is handled in Weekly Schedule
		# ensure a client is linked (dynamic)
		if not self.client:
			frappe.throw("Please set Client.")

		# Restrict cancellation to Sales Manager / System Manager only (only when setting status to Cancelled manually)
		if self.status == "Cancelled" and self.docstatus != 2:
			allowed_cancel_roles = {"Sales Manager", "System Manager"}
			user_roles = set(frappe.get_roles())
			if not (user_roles & allowed_cancel_roles):
				frappe.throw("Only a Sales Manager can cancel a Visit.")

		# enforce outcome when completing
		if self.status == "Completed" and not self.get("visit_outcome"):
			frappe.throw("Visit Outcome is required when completing a Visit.")

		# enforce geolocation on completion if enabled in settings
		if self.status == "Completed" and require_geolocation_on_completion() and not self.get("location"):
			frappe.throw("Location is required upon completion (per settings).")

		# enforce check-in presence on completion unless the performing user is exempt by role
		# Note: exemption applies to the actor (back-office) to allow closing on behalf of field exec
		if self.status == "Completed" and is_checkin_mandatory_for_user(frappe.session.user):
			if not self.get("check_in_time"):
				frappe.throw("Check-in is required before completing this Visit (per settings).")

		# Maintenance validation: enforce details and either Support Issue or Maintenance Visit
		try:
			purpose = (self.get("subject") or "").strip().lower()
			if purpose == "maintenance" and (self.get("client_type") == "Customer"):
				# Details must be provided
				if not self.get("maintenance_details"):
					frappe.throw("Maintenance Details are required for maintenance visits to Customers.")
				# Before completion, Maintenance Visit link isn't available; require Support Issue
				if self.get("status") != "Completed":
					if not self.get("support_issue"):
						frappe.throw("Link a Support Issue for maintenance visits before completion, or complete the visit to link a Maintenance Visit.")
				else:
					# On completion, if neither Support Issue nor Maintenance Visit, try auto-create MV
					if not (self.get("support_issue") or self.get("maintenance_visit")):
						self._auto_create_maintenance_visit_if_needed()
						if not (self.get("support_issue") or self.get("maintenance_visit")):
							frappe.throw("Provide either a Support Issue or a Maintenance Visit when completing a maintenance visit.")
		except Exception:
			pass

		# auto-calc duration if both times exist
		try:
			if self.get("check_in_time") and self.get("check_out_time"):
				start = self.get("check_in_time")
				end = self.get("check_out_time")
				mins = max(0, int((end - start).total_seconds() // 60))
				self.set("visit_duration_minutes", mins)
		except Exception:
			pass

		# enforce report content upon completion - at least one field must be filled
		if self.status == "Completed":
			required_fields = [
				"additional_notes",
				"competitor_info",
				"existing_fleet",
				"requirements_received",
				"future_prospects",
				"product_target",
				"customer_feedback",
				"report_attachment"
			]
			if not any(self.get(field) for field in required_fields):
				frappe.throw(
					"At least one of the following fields must be filled before marking visit as completed: "
					"Additional Notes, Competitor Information, Existing Fleet Information, "
					"Any Requirements Received, Future Prospects, Potential Product Target, "
					"Customer Feedback, or Report Attachment."
				)
	
	# Attendance integration: Check-in/Check-out
	def _get_employee(self) -> str:
		"""Resolve Employee for the visit: use current logged-in user.

		Returns Employee name or throws if not found.
		"""
		user = frappe.session.user
		emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not emp:
			frappe.throw(f"No Employee linked to user {user}. Please link an Employee to proceed.")
		return emp

	def _ensure_attendance(self, emp: str, when=None):
		from frappe.utils import getdate
		when = when or now_datetime()
		att_name = frappe.db.get_value(
			"Attendance",
			{"employee": emp, "attendance_date": getdate(when)},
			"name",
		)
		if att_name:
			return frappe.get_doc("Attendance", att_name)
		# Create a basic attendance if not exists
		att = frappe.get_doc({
			"doctype": "Attendance",
			"employee": emp,
			"attendance_date": getdate(when),
			"status": "Present",
		})
		att.insert(ignore_permissions=True)
		return att

	@whitelist()
	def check_in(self, photo_data=None, photo_filename=None, location=None):
		"""Create Employee Checkin (IN), attach photo (if provided), set fields, and save once.
		
		Also captures location if provided in form context.
		"""
		if self.check_in_time:
			frappe.throw("Already checked in.")

		# Optional: attach photo provided by client in the same request to avoid version mismatch
		photo_data = photo_data or frappe.form_dict.get("photo_data")
		photo_filename = photo_filename or frappe.form_dict.get("photo_filename") or "check_in_photo.jpg"
		_attach_attempted = bool(photo_data)
		_attach_error = None
		if photo_data:
			try:
				payload = photo_data
				if isinstance(payload, str) and payload.startswith("data:"):
					_, _, payload = payload.partition(",")

				from frappe.utils.file_manager import save_file
				result = save_file(
					fname=photo_filename,
					content=payload,
					dt=self.doctype,
					dn=self.name,
					decode=True,
					is_private=1,
					df="check_in_photo",
				)
				# Only after successful attach, prune older attachments to avoid duplicates
				if result and getattr(result, "name", None):
					existing_files = frappe.get_all(
						"File",
						filters={
							"attached_to_doctype": self.doctype,
							"attached_to_name": self.name,
							"attached_to_field": ["in", ["check_in_photo", None, ""]],
							"name": ["!=", result.name],
						},
						pluck="name",
					)
					for fname in existing_files:
						frappe.delete_doc("File", fname, ignore_permissions=True)

				self.check_in_photo = getattr(result, "file_url", None) or self.check_in_photo
			except Exception as e:
				_attach_error = frappe.utils.cstr(e)
				frappe.log_error(_attach_error, "Visit Check-in Photo Attach Error")

		# Ensure field is hydrated from existing attachments before validating
		self._sync_photo_field("check_in_photo")

		# Validate required photo after attempting attach
		if is_photo_required(checkout=False) and not self.get("check_in_photo"):
			if _attach_attempted:
				frappe.throw("Failed to attach photo for Check-in. Please retry.")
			else:
				frappe.throw("Attendance photo is required for Check-in.")
		
		# Capture location from form_dict if provided (from browser geolocation)
		location_data = location or frappe.form_dict.get("location")
		location_obj = None
		if location_data and not self.get("check_in_location"):
			try:
				import json
				if isinstance(location_data, str):
					location_obj = json.loads(location_data)
				else:
					location_obj = location_data
				
				if isinstance(location_obj, dict) and location_obj.get("lat") and location_obj.get("lng"):
					# Format as readable text with coordinates
					self.check_in_location = f"Latitude: {location_obj['lat']}, Longitude: {location_obj['lng']}"
			except Exception:
				pass  # Silently ignore location errors
		
		emp = self._get_employee()
		when = now_datetime()
		# Employee Checkin (HRMS)
		ecin = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp,
			"time": when,
			"log_type": "IN",
			"device_id": "Visit",
			"skip_auto_attendance": 0,
		})
		# Attach location to Employee Checkin if available
		if location_obj and isinstance(location_obj, dict):
			if location_obj.get("lat"):
				ecin.latitude = location_obj["lat"]
			if location_obj.get("lng"):
				ecin.longitude = location_obj["lng"]
		ecin.insert(ignore_permissions=True)
		
		# Update visit fields in memory (not db_set to avoid version conflicts)
		self.check_in_time = when
		self.status = "In Progress"
		
		# Log entry
		self.append("visit_logs", {"timestamp": when, "activity": "Check-in", "user": frappe.session.user})
		
		# Save document once with all changes
		self.save(ignore_permissions=True)
		
		# Update attendance
		att = self._ensure_attendance(emp, when)
		meta = frappe.get_meta("Attendance")
		if meta.has_field("in_time") and not att.get("in_time"):
			att.db_set("in_time", when)
		
		return {
			"employee": emp,
			"check_in_time": when,
			"employee_checkin": ecin.name,
		}

	@whitelist()
	def check_out(self, photo_data=None, photo_filename=None, location=None):
		"""Create Employee Checkin (OUT), attach photo (if provided), set fields, and save once."""
		if not self.check_in_time:
			frappe.throw("Check-in first before checking out.")
		if self.check_out_time:
			frappe.throw("Already checked out.")

		# Optional: attach photo provided by client in the same request
		photo_data = photo_data or frappe.form_dict.get("photo_data")
		photo_filename = photo_filename or frappe.form_dict.get("photo_filename") or "check_out_photo.jpg"
		_attach_attempted = bool(photo_data)
		_attach_error = None
		if photo_data:
			try:
				payload = photo_data
				if isinstance(payload, str) and payload.startswith("data:"):
					_, _, payload = payload.partition(",")

				from frappe.utils.file_manager import save_file
				result = save_file(
					fname=photo_filename,
					content=payload,
					dt=self.doctype,
					dn=self.name,
					decode=True,
					is_private=1,
					df="check_out_photo",
				)
				# Only after successful attach, prune older attachments to avoid duplicates
				if result and getattr(result, "name", None):
					existing_files = frappe.get_all(
						"File",
						filters={
							"attached_to_doctype": self.doctype,
							"attached_to_name": self.name,
							"attached_to_field": ["in", ["check_out_photo", None, ""]],
							"name": ["!=", result.name],
						},
						pluck="name",
					)
					for fname in existing_files:
						frappe.delete_doc("File", fname, ignore_permissions=True)

				self.check_out_photo = getattr(result, "file_url", None) or self.check_out_photo
			except Exception as e:
				_attach_error = frappe.utils.cstr(e)
				frappe.log_error(_attach_error, "Visit Check-out Photo Attach Error")

		# Ensure field is hydrated from existing attachments before validating
		self._sync_photo_field("check_out_photo")

		# Validate required photo after attempting attach
		if is_photo_required(checkout=True) and not self.get("check_out_photo"):
			if _attach_attempted:
				frappe.throw("Failed to attach photo for Check-out. Please retry.")
			else:
				frappe.throw("Attendance photo is required for Check-out.")
		
		# Capture location from form_dict if provided (from browser geolocation)
		location_data = location or frappe.form_dict.get("location")
		location_obj = None
		if location_data and not self.get("check_out_location"):
			try:
				import json
				if isinstance(location_data, str):
					location_obj = json.loads(location_data)
				else:
					location_obj = location_data
				
				if isinstance(location_obj, dict) and location_obj.get("lat") and location_obj.get("lng"):
					# Format as readable text with coordinates
					self.check_out_location = f"Latitude: {location_obj['lat']}, Longitude: {location_obj['lng']}"
			except Exception:
				pass  # Silently ignore location errors
		
		emp = self._get_employee()
		when = now_datetime()
		ecout = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp,
			"time": when,
			"log_type": "OUT",
			"device_id": "Visit",
			"skip_auto_attendance": 0,
		})
		# Attach location to Employee Checkin if available
		if location_obj and isinstance(location_obj, dict):
			if location_obj.get("lat"):
				ecout.latitude = location_obj["lat"]
			if location_obj.get("lng"):
				ecout.longitude = location_obj["lng"]
		ecout.insert(ignore_permissions=True)
		
		# Update visit fields in memory (not db_set to avoid version conflicts)
		self.check_out_time = when
		self.status = "Completed"
		
		# Compute visit duration
		if self.check_in_time and self.check_out_time:
			# Convert to datetime objects if they are strings
			start = frappe.utils.get_datetime(self.check_in_time)
			end = frappe.utils.get_datetime(self.check_out_time)
			mins = max(0, int((end - start).total_seconds() // 60))
			self.visit_duration_minutes = mins
		
		# Log entry
		self.append("visit_logs", {"timestamp": when, "activity": "Check-out", "user": frappe.session.user})
		
		# Save document once with all changes
		self.save(ignore_permissions=True)
		
		att = self._ensure_attendance(emp, when)
		meta = frappe.get_meta("Attendance")
		if meta.has_field("out_time"):
			att.db_set("out_time", when)
		return {
			"employee": emp,
			"check_out_time": when,
			"employee_checkin": ecout.name,
		}

	@whitelist()
	def create_maintenance_visit_now(self) -> str | None:
		"""Manually create and link a Maintenance Visit using current Visit data.

		Only allowed for maintenance purpose, customer client type, Completed status, and when not already linked.
		Returns the Maintenance Visit name on success.
		"""
		mv = self._auto_create_maintenance_visit_if_needed()
		if not mv:
			frappe.throw("Cannot create Maintenance Visit. Ensure this Visit is Completed, has purpose 'Maintenance', client type is 'Customer', and no Maintenance Visit is linked yet.")
		# Save the Visit record with the link for consistency
		try:
			self.save(ignore_permissions=True)
		except Exception:
			pass
		return mv

	# Expose address fetch as a doc method for run_doc_method compatibility
	@whitelist()
	def get_client_default_address(self, client_type: str | None = None, client: str | None = None):
		from .visit import get_client_default_address as _fetch
		return _fetch(client_type or self.client_type, client or self.client)


@whitelist()
def test_b():
	"""Test B: create a minimal CRM Lead and a Visit, then delete the Visit.

	Returns a summary dict with created names and deletion status.
	"""
	from frappe.utils import now_datetime
	# Create a simple CRM Lead (person) to link as client
	lead = frappe.get_doc({
		"doctype": "CRM Lead",
		"first_name": "Test",
		"email": "test@example.com",
	})
	lead.insert(ignore_permissions=True)

	# Create a minimal Visit (status Planned) linked to the Lead
	visit = frappe.get_doc({
		"doctype": "Visit",
		"status": "Planned",
		"scheduled_time": now_datetime(),
		"assigned_to": "Administrator",
		"client_type": "CRM Lead",
		"client": lead.name,
		"subject": "Follow-up",
	})
	visit.insert(ignore_permissions=True)
	visit_name = visit.name

	# Delete the Visit
	frappe.delete_doc("Visit", visit_name, ignore_permissions=True)

	return {
		"lead": lead.name,
		"visit": visit_name,
		"visit_deleted": not frappe.db.exists("Visit", visit_name),
	}


@whitelist()
def has_permission_api(name: str, ptype: str | None = None, user: str | None = None) -> bool:
	"""RPC-friendly wrapper using core permission evaluation (no custom override)."""
	user = user or frappe.session.user
	doc = frappe.get_doc("Visit", name)
	return frappe.has_permission(doctype="Visit", ptype=ptype, doc=doc, user=user)


@whitelist()
def get_client_default_address(client_type: str, client: str) -> str | None:
	"""Return a default Address name for the given client, if any.

	Tries to find an Address linked via Address Link child table.
	Prefers primary addresses, falls back to first found.
	"""
	if not client_type or not client:
		return None
	# Best-effort query via child table filters
	try:
		# Prefer primary address
		rows = frappe.get_all(
			"Address",
			filters={
				"links.link_doctype": client_type,
				"links.link_name": client,
				"is_primary_address": 1,
			},
			fields=["name"],
			limit=1,
		)
		if rows:
			return rows[0]["name"]
		# Any address
		rows = frappe.get_all(
			"Address",
			filters={
				"links.link_doctype": client_type,
				"links.link_name": client,
			},
			fields=["name"],
			limit=1,
		)
		if rows:
			return rows[0]["name"]
	except Exception:
		# Some DB backends may not support child table filtering this way; ignore errors
		pass
	return None


@whitelist()
def get_contact_query(doctype, txt, searchfield, start, page_len, filters):
	"""Filter contacts based on client_type and client from the form.
	
	Frappe passes current form values in filters dict.
	Returns contacts linked to the selected client.
	"""
	import json
	
	client_type = None
	client = None
	
	# Parse filters - can be JSON string or dict
	try:
		if isinstance(filters, str):
			if filters.startswith('['):
				# Array format: [ ["field", "operator", "value"] ]
				filters_array = json.loads(filters)
				for f in filters_array:
					if isinstance(f, list) and len(f) >= 3:
						if f[0] == "client_type":
							client_type = f[2]
						elif f[0] == "client":
							client = f[2]
			else:
				# Object format
				filters_obj = json.loads(filters)
				client_type = filters_obj.get("client_type")
				client = filters_obj.get("client")
		elif isinstance(filters, dict):
			client_type = filters.get("client_type")
			client = filters.get("client")
	except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
		pass
	
	# If no filters, try to get from form context
	if not client_type or not client:
		client_type = frappe.form_dict.get("client_type")
		client = frappe.form_dict.get("client")
	
	# Empty result if no client selected
	if not client_type or not client:
		return []
	
	# Build query using Dynamic Link for all client types
	query = """
		SELECT DISTINCT c.name
		FROM `tabContact` c
		WHERE EXISTS (
			SELECT 1 FROM `tabDynamic Link` dl 
			WHERE dl.parent = c.name 
			AND dl.parenttype = 'Contact'
			AND dl.link_doctype = %(client_type)s
			AND dl.link_name = %(client)s
		)
	"""
	
	# Add search
	if txt:
		query += """ AND (c.name LIKE %(txt)s OR c.first_name LIKE %(txt)s OR c.last_name LIKE %(txt)s)"""
	
	query += """ LIMIT %(start)s, %(page_len)s"""
	
	params = {
		"client": client,
		"client_type": client_type,
		"txt": f"%{txt}%" if txt else "%",
		"start": int(start),
		"page_len": int(page_len),
	}
	
	return frappe.db.sql(query, params)


@whitelist()
def get_filtered_contacts(client_type, client):
	"""Simple method to get contacts filtered by client_type and client.
	
	Can be called directly from the form via frappe.call when client/client_type changes.
	"""
	if not client_type or not client:
		return []
	
	# Use Dynamic Link for all client types
	query = """
		SELECT DISTINCT c.name
		FROM `tabContact` c
		WHERE EXISTS (
			SELECT 1 FROM `tabDynamic Link` dl 
			WHERE dl.parent = c.name 
			AND dl.parenttype = 'Contact'
			AND dl.link_doctype = %(client_type)s
			AND dl.link_name = %(client)s
		)
		ORDER BY c.name
	"""
	
	params = {
		"client": client,
		"client_type": client_type,
	}
	
	results = frappe.db.sql(query, params)
	return [r[0] for r in results]

@whitelist()
def get_address_query(doctype, txt, searchfield, start, page_len, filters):
	"""Filter addresses based on client_type and client from the form.
	
	Returns addresses linked to the selected client via Dynamic Links.
	"""
	import json
	
	client_type = None
	client = None
	
	# Parse filters - can be JSON string or dict
	try:
		if isinstance(filters, str):
			filters_obj = json.loads(filters)
			client_type = filters_obj.get("client_type")
			client = filters_obj.get("client")
		elif isinstance(filters, dict):
			client_type = filters.get("client_type")
			client = filters.get("client")
	except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
		pass
	
	# If no filters, try to get from form context
	if not client_type or not client:
		client_type = frappe.form_dict.get("client_type")
		client = frappe.form_dict.get("client")
	
	# Empty result if no client selected
	if not client_type or not client:
		return []
	
	# Build query using Dynamic Link
	query = """
		SELECT DISTINCT a.name
		FROM `tabAddress` a
		WHERE EXISTS (
			SELECT 1 FROM `tabDynamic Link` dl 
			WHERE dl.parent = a.name 
			AND dl.parenttype = 'Address'
			AND dl.link_doctype = %(client_type)s
			AND dl.link_name = %(client)s
		)
	"""
	
	# Add search
	if txt:
		query += """ AND (a.name LIKE %(txt)s OR a.address_title LIKE %(txt)s OR a.city LIKE %(txt)s)"""
	
	query += """ LIMIT %(start)s, %(page_len)s"""
	
	params = {
		"client": client,
		"client_type": client_type,
		"txt": f"%{txt}%" if txt else "%",
		"start": int(start),
		"page_len": int(page_len),
	}
	
	return frappe.db.sql(query, params)