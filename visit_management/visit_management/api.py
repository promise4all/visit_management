from __future__ import annotations

import base64
from datetime import timedelta

import frappe
from frappe import _, whitelist
from frappe.utils import now_datetime


def _monday_of_week(d):
    try:
        return d - timedelta(days=d.weekday())
    except Exception:
        return d


def _format_time(val) -> str:
    try:
        # val can be a str "HH:MM:SS" or time object
        s = str(val)
        return s[:5] if len(s) >= 5 else s
    except Exception:
        return ""


def _current_user() -> str:
    try:
        return frappe.session.user
    except Exception:
        return "Guest"


@whitelist()
def get_weekly_schedule(week_start: str | None = None) -> list[dict]:
    """Return flattened schedule rows for the current user's current week.

    Each item contains: name, schedule, day, time_slot, client, purpose, approved, status, visit.
    """
    user = _current_user()
    # compute week start (Monday) if not provided
    if not week_start:
        d = now_datetime().date()
        week_start = _monday_of_week(d).isoformat()

    # find an existing schedule for user + week
    schedule_name = frappe.db.get_value(
        "Weekly Schedule", {"user": user, "week_start": week_start}, "name"
    )
    if not schedule_name:
        # Fallback to the latest available schedule for the user
        latest = frappe.db.get_all(
            "Weekly Schedule",
            filters={"user": user},
            fields=["name", "week_start"],
            order_by="week_start desc",
            limit=1,
        )
        if latest:
            schedule_name = latest[0]["name"]
        else:
            return []

    # load details directly via child table to avoid heavy parent serialization
    rows = frappe.get_all(
        "Weekly Schedule Detail",
        filters={"parent": schedule_name},
        fields=[
            "name",
            "day",
            "time as time_value",
            "client",
            "purpose",
            "approved",
            "visit",
        ],
        order_by="idx asc",
    )

    # enrich rows with derived fields expected by the UI
    for r in rows:
        r["schedule"] = schedule_name
        r["time_slot"] = _format_time(r.pop("time_value", ""))
        r["status"] = "Approved" if r.get("approved") else "Pending"

    # sort by day-of-week then time for stable display
    weekday_idx = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    rows.sort(key=lambda x: (weekday_idx.get(x.get("day"), 0), x.get("time_slot") or ""))
    return rows


@whitelist()
def approve_weekly_row(name: str, create_visit: int | None = None) -> dict:
    """Approve a single Weekly Schedule Detail row.

    - Requires Sales Manager/System Manager role (enforced by underlying method).
    - Optionally create a Visit immediately when approved (create_visit=1).
    """
    if not name:
        frappe.throw(_("Row name is required."))

    # locate parent schedule
    schedule = frappe.db.get_value("Weekly Schedule Detail", name, "parent")
    if not schedule:
        frappe.throw(_("Parent Weekly Schedule not found for row {0}").format(name))

    from visit_management.visit_management.doctype.weekly_schedule.weekly_schedule import (
        approve_rows,
    )

    res = approve_rows(schedule=schedule, rows=[name], create_visits=bool(create_visit))
    return res


@whitelist()
def create_planned_visits(week_start: str | None = None) -> dict:
    """Create Visit documents for all approved rows in the user's schedule for the week.

    If no schedule exists for the computed week, returns an empty result.
    """
    user = _current_user()
    if not week_start:
        d = now_datetime().date()
        week_start = _monday_of_week(d).isoformat()

    schedule_name = frappe.db.get_value(
        "Weekly Schedule", {"user": user, "week_start": week_start}, "name"
    )
    if not schedule_name:
        return {"created": [], "skipped": [], "message": "No weekly schedule found."}

    from visit_management.visit_management.doctype.weekly_schedule.weekly_schedule import (
        create_visits_for_approved_rows,
    )

    res = create_visits_for_approved_rows(schedule=schedule_name)
    return res


@whitelist()
def attach_visit_photo(
    filename: str,
    filedata,
    doctype: str,
    docname: str,
    fieldname: str | None = None,
    is_private: int | bool = 0,
):
    """Attach a photo to a Visit, accepting data URLs or raw base64.

    This method normalizes the incoming payload to plain base64 and always sets
    ``decode_base64=True`` when delegating to ``frappe.client.attach_file`` so the
    content reaches the File doctype as bytes.
    """

    if not filename or not filedata:
        frappe.throw(_("Filename and filedata are required."))

    # Normalize to base64 text
    payload: str
    if isinstance(filedata, str):
        if filedata.startswith("data:"):
            _, _, b64 = filedata.partition(",")
            payload = b64 or ""
        else:
            payload = filedata
    elif isinstance(filedata, (bytes, bytearray)):
        payload = base64.b64encode(filedata).decode()
    else:
        frappe.throw(_("Unsupported filedata type: {0}").format(type(filedata).__name__))

    if not payload:
        frappe.throw(_("No file content found."))

    # Attach file using frappe.client.attach_file
    # This returns {file_url: "...", file_name: "..."}
    result = frappe.client.attach_file(
        filename=filename,
        filedata=payload,
        doctype=doctype,
        docname=docname,
        decode_base64=True,
    )
    
    # If fieldname provided, set it on the document
    if fieldname:
        frappe.db.set_value(doctype, docname, fieldname, result.get("file_url"))
    
    return result
