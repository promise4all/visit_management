from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime, nowdate


def update_overdue_status():
    """Deprecated: Overdue status removed. Kept for backward compatibility (no-op)."""
    return


def cleanup_old_drafts(days: int = 90):
    """Daily: delete Draft Visits older than N days to keep db tidy."""
    cutoff = add_days(nowdate(), -days)
    old_drafts = frappe.get_all(
        "Visit",
        filters={"docstatus": 0, "modified": ["<", cutoff]},
        pluck="name",
    )
    for name in old_drafts:
        try:
            frappe.delete_doc("Visit", name, ignore_permissions=True, force=True)
        except Exception:
            frappe.log_error(title="Visit Cleanup Failed", message=f"Could not delete Visit {name}")


def send_visit_reminders(lookahead_days: int = 1):
    """Daily: email Assigned To users about upcoming visits in next N days."""
    from_date = nowdate()
    to_date = add_days(from_date, lookahead_days)
    visits = frappe.get_all(
        "Visit",
        filters={
            "status": ["in", ["Planned", "In Progress"]],
            "scheduled_time": ["between", [from_date, to_date]],
        },
        fields=["name", "assigned_to", "scheduled_time"],
    )
    for v in visits:
        if not v.assigned_to:
            continue
        try:
            frappe.sendmail(
                recipients=[v.assigned_to],
                subject=f"Visit Reminder: {v.name}",
                message=f"You have a visit scheduled at {v.scheduled_time}.",
            )
        except Exception:
            frappe.log_error(
                title="Visit Reminder Failed",
                message=f"Could not send reminder for Visit {v.name} to {v.assigned_to}",
            )
