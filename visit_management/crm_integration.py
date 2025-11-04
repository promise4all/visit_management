from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def _update_last_visit_on_crm(doc):
    """
    Update a conservative "last_visit_date" field on linked CRM records (Lead/Contact/Customer) if present.
    If the field doesn't exist on the target doctype, fail silently with a log.
    """
    ts = (doc.scheduled_time or now_datetime())
    targets = []
    if getattr(doc, "lead", None):
        targets.append(("Lead", doc.lead))
    if getattr(doc, "contact", None):
        targets.append(("Contact", doc.contact))
    if getattr(doc, "customer", None):
        targets.append(("Customer", doc.customer))

    for doctype, name in targets:
        try:
            # attempt to set a conventional field; ignore if missing
            if frappe.db.has_column(doctype, "last_visit_date"):
                frappe.db.set_value(doctype, name, "last_visit_date", ts)
        except Exception:
            frappe.log_error(
                title="Visit CRM Sync Failed",
                message=f"Could not update last_visit_date on {doctype} {name}",
            )


def on_visit_validate(doc, method=None):
    """Hook: validate"""
    _update_last_visit_on_crm(doc)


def on_visit_update(doc, method=None):
    """Hook: on_update"""
    _update_last_visit_on_crm(doc)


def on_visit_after_insert(doc, method=None):
    """Hook: after_insert"""
    _update_last_visit_on_crm(doc)


def on_visit_trash(doc, method=None):
    """Hook: on_trash"""
    # no-op; could add reverse sync or audit later
    pass
