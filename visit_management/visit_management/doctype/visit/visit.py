from __future__ import annotations

import frappe
from frappe import whitelist
from frappe.model.document import Document
from frappe.utils import now_datetime
from visit_management.visit_management.settings_utils import (
	is_photo_required,
	require_geolocation_on_completion,
	is_checkin_mandatory_for_user,
)


class Visit(Document):
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
		# ensure a client is linked (dynamic)
		if not self.client:
			frappe.throw("Please set Client.")

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

		# enforce report content upon completion
		if self.status == "Completed" and not self.get("report_summary"):
			frappe.throw("Report Summary is required upon completion of a Visit.")
	
	# Attendance integration: Check-in/Check-out
	def _get_employee(self) -> str:
		"""Resolve Employee for the visit: prefer assigned_to's employee, else session user.

		Returns Employee name or throws if not found.
		"""
		user = self.assigned_to or frappe.session.user
	temp = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not emp:
			frappe.throw("No Employee linked to user {0}. Please link an Employee to proceed.".format(user))
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
	def check_in(self):
		"""Create Employee Checkin (IN) and set check_in_time; ensure Attendance."""
		if self.check_in_time:
			frappe.throw("Already checked in.")
		if is_photo_required(checkout=False) and not self.get("check_in_photo"):
			frappe.throw("Attendance photo is required for Check-in.")
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
		ecin.insert(ignore_permissions=True)
		# Update visit and attendance
		self.db_set("check_in_time", when)
		att = self._ensure_attendance(emp, when)
		meta = frappe.get_meta("Attendance")
		if meta.has_field("in_time") and not att.get("in_time"):
			att.db_set("in_time", when)
		# Log entry
		try:
			self.append("visit_logs", {"timestamp": when, "activity": "Check-in", "user": frappe.session.user})
			self.save(ignore_permissions=True)
		except Exception:
			pass
		return {
			"employee": emp,
			"check_in_time": when,
			"employee_checkin": ecin.name,
		}

	@whitelist()
	def check_out(self):
		"""Create Employee Checkin (OUT) and set check_out_time; update Attendance."""
		if not self.check_in_time:
			frappe.throw("Check-in first before checking out.")
		if self.check_out_time:
			frappe.throw("Already checked out.")
		if is_photo_required(checkout=True) and not self.get("check_out_photo"):
			frappe.throw("Attendance photo is required for Check-out.")
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
		ecout.insert(ignore_permissions=True)
		self.db_set("check_out_time", when)
		att = self._ensure_attendance(emp, when)
		meta = frappe.get_meta("Attendance")
		if meta.has_field("out_time"):
			att.db_set("out_time", when)
		# compute and persist duration
		try:
			if self.get("check_in_time") and self.get("check_out_time"):
				start = self.get("check_in_time")
				end = self.get("check_out_time")
				mins = max(0, int((end - start).total_seconds() // 60))
				self.db_set("visit_duration_minutes", mins)
		except Exception:
			pass
		# Log entry
		try:
			self.append("visit_logs", {"timestamp": when, "activity": "Check-out", "user": frappe.session.user})
			self.save(ignore_permissions=True)
		except Exception:
			pass
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
def has_permission(doc, ptype=None, user=None):
	"""Custom permission: assigned user or system manager gets access in addition to role permissions.

	Note: This function is also whitelisted for optional RPC calls; when invoked via hooks,
	Frappe will pass a Document instance for `doc`.
	"""
	user = user or frappe.session.user
	if not doc:
		return False
	if user == "Administrator":
		return True
	try:
		if getattr(doc, "assigned_to", None) and doc.assigned_to == user:
			return True
	except Exception:
		pass
	# fallback to role-based permissions
	return frappe.has_permission(doctype=doc.doctype, ptype=ptype, doc=doc, user=user)


@whitelist()
def has_permission_api(name: str, ptype: str | None = None, user: str | None = None) -> bool:
	"""RPC-friendly wrapper to check permission by document name."""
	doc = frappe.get_doc("Visit", name)
	return has_permission(doc, ptype=ptype, user=user)


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
