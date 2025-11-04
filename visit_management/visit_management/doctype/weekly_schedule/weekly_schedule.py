from __future__ import annotations

import frappe
from frappe import _
from frappe import whitelist
from frappe.model.document import Document
from frappe.utils import now_datetime
from datetime import datetime, timedelta, time as dtime, date as ddate


class WeeklySchedule(Document):
    def before_save(self):
        """Auto-manage parent status based on child approvals if not explicitly set."""
        try:
            # stamp approver metadata if missing and enforce role
            is_manager = frappe.has_role("Sales Manager") or frappe.has_role("System Manager")
            for row in (self.get("details") or []):
                if row.get("approved") and not row.get("approved_by"):
                    if not is_manager:
                        frappe.throw(_("Only Sales Manager or System Manager can approve rows."), frappe.PermissionError)
                    row.approved_by = frappe.session.user
                    row.approved_on = now_datetime()

            approved = [row for row in (self.get("details") or []) if row.get("approved")]
            total = len(self.get("details") or [])
            if total:
                if len(approved) == 0 and self.status not in {"Draft", "Rejected"}:
                    self.status = "Draft"
                elif 0 < len(approved) < total:
                    self.status = "Pending Approval"
                elif len(approved) == total:
                    self.status = "Approved"
        except Exception:
            pass


def _ensure_manager_role(user: str | None = None):
    user = user or frappe.session.user
    try:
        roles = set(frappe.get_roles(user))
    except Exception:
        roles = set()
    if roles.isdisjoint({"Sales Manager", "System Manager"}):
        frappe.throw(_("Only Sales Manager or System Manager can approve schedules."), frappe.PermissionError)


WEEKDAY_IDX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def _to_time_obj(val) -> dtime:
    if isinstance(val, dtime):
        return val
    if isinstance(val, str) and val:
        # try HH:MM:SS then HH:MM
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(val, fmt).time()
            except Exception:
                pass
    # fallback 09:00
    return dtime(9, 0, 0)


def _compute_scheduled_dt(week_start, day: str, tm) -> datetime:
    # week_start may be str or date
    if isinstance(week_start, str):
        try:
            week_start = datetime.strptime(week_start, "%Y-%m-%d").date()
        except Exception:
            week_start = now_datetime().date()
    elif isinstance(week_start, datetime):
        week_start = week_start.date()
    elif not isinstance(week_start, ddate):
        week_start = now_datetime().date()
    offset = WEEKDAY_IDX.get(day or "Monday", 0)
    t = _to_time_obj(tm)
    target_date = week_start + timedelta(days=offset)
    return datetime.combine(target_date, t)


def _create_visit_from_row(schedule_doc: Document, row: Document) -> str | None:
    """Create a Visit from the given Weekly Schedule Detail row. Returns Visit name or None."""
    # required fields for Visit
    if not (row.get("client_type") and row.get("client") and row.get("purpose")):
        return None
    assigned_to = schedule_doc.get("user") or frappe.session.user
    scheduled_time = _compute_scheduled_dt(schedule_doc.get("week_start"), row.get("day"), row.get("time"))

    visit = frappe.get_doc({
        "doctype": "Visit",
        "status": "Planned",
        "scheduled_time": scheduled_time,
        "assigned_to": assigned_to,
        "client_type": row.get("client_type"),
        "client": row.get("client"),
        "subject": row.get("purpose"),
        "notes": row.get("notes") or "",
    })

    # Maintenance-specific fields
    try:
        purpose = (row.get("purpose") or "").strip().lower()
        if purpose == "maintenance":
            if row.get("support_issue"):
                visit.set("support_issue", row.get("support_issue"))
            if row.get("maintenance_details"):
                visit.set("maintenance_details", row.get("maintenance_details"))
    except Exception:
        pass

    visit.insert(ignore_permissions=True)
    return visit.name


@whitelist()
def approve_rows(schedule: str, rows: list[str] | None = None, create_visits: bool | None = None) -> dict:
    """Approve selected detail rows on a Weekly Schedule.

    - Only Sales Manager or System Manager can approve.
    - Automatically records approved_by and approved_on.
    - Optionally creates Visit for each newly approved row (default from settings).
    """
    _ensure_manager_role()
    doc = frappe.get_doc("Weekly Schedule", schedule)
    rows = set(rows or [])

    # settings for auto-creation
    auto_create = create_visits
    if auto_create is None:
        try:
            from visit_management.visit_management.settings_utils import get_settings

            auto_create = bool(get_settings().get("auto_create_visits_from_schedule", True))
        except Exception:
            auto_create = True

    approved_count = 0
    created = []
    for row in (doc.get("details") or []):
        if rows and row.name not in rows:
            continue
        if not row.get("approved"):
            row.approved = 1
            row.approved_by = frappe.session.user
            row.approved_on = now_datetime()
            approved_count += 1
        if auto_create and not row.get("visit"):
            vname = _create_visit_from_row(doc, row)
            if vname:
                row.visit = vname
                created.append(vname)

    # update parent status
    try:
        total = len(doc.get("details") or [])
        approved = len([r for r in (doc.get("details") or []) if r.get("approved")])
        if total and approved == total:
            doc.status = "Approved"
        elif approved > 0:
            doc.status = "Pending Approval"
        else:
            doc.status = "Draft"
    except Exception:
        pass

    doc.save(ignore_permissions=True)
    return {
        "approved": approved_count,
        "created": created,
        "status": doc.status,
    }


@whitelist()
def create_visits_for_approved_rows(schedule: str) -> dict:
    """Create planned Visits for all approved rows that don't already have a Visit."""
    _ensure_manager_role()
    doc = frappe.get_doc("Weekly Schedule", schedule)
    created = []
    skipped = []
    for row in (doc.get("details") or []):
        if not row.get("approved"):
            continue
        if row.get("visit"):
            skipped.append(row.get("name"))
            continue
        vname = _create_visit_from_row(doc, row)
        if vname:
            row.visit = vname
            created.append(vname)
    doc.save(ignore_permissions=True)
    return {"created": created, "skipped": skipped}
