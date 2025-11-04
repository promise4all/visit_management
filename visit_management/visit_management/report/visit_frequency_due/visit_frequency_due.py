import frappe
from frappe.utils import getdate, now_datetime


def execute(filters=None):
    cols = [
        {"fieldname": "client_type", "label": "Client Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "client", "label": "Client", "fieldtype": "Dynamic Link", "options": "client_type", "width": 220},
        {"fieldname": "requires_regular_visits", "label": "Requires Regular", "fieldtype": "Check", "width": 90},
        {"fieldname": "visit_frequency", "label": "Frequency", "fieldtype": "Data", "width": 110},
        {"fieldname": "last_visit", "label": "Last Visit", "fieldtype": "Datetime", "width": 170},
        {"fieldname": "due_date", "label": "Due Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "is_overdue", "label": "Overdue", "fieldtype": "Check", "width": 80},
    ]

    data = []

    def get_last_visit_for(client_doctype: str, client_name: str):
        dt = frappe.db.sql(
            """
            select coalesce(max(check_out_time), max(scheduled_time))
            from `tabVisit`
            where status='Completed' and client_type=%s and client=%s
            """,
            (client_doctype, client_name),
        )
        return (dt[0][0] if dt and dt[0] and dt[0][0] else None)

    def add_rows_for(doctype: str, name_field: str = "name"):
        freq_clients = frappe.get_all(
            doctype,
            filters={"requires_regular_visits": 1},
            fields=[name_field, "visit_frequency", "requires_regular_visits"],
        )
        today = getdate()
        for r in freq_clients:
            client_name = r.get(name_field)
            last = get_last_visit_for(doctype, client_name)
            due = due_date_from(last, r.get("visit_frequency"))
            is_overdue = (not due) or (due < today)
            data.append(
                {
                    "client_type": doctype,
                    "client": client_name,
                    "requires_regular_visits": 1,
                    "visit_frequency": r.get("visit_frequency"),
                    "last_visit": last,
                    "due_date": due,
                    "is_overdue": 1 if is_overdue else 0,
                }
            )

    def due_date_from(last_dt, freq: str):
        import datetime
        if not last_dt:
            return None
        if isinstance(last_dt, str):
            try:
                last_dt = datetime.datetime.fromisoformat(last_dt)
            except Exception:
                last_dt = now_datetime()
        mapping = {
            "Weekly": 7,
            "Biweekly": 14,
            "Monthly": 30,
            "Quarterly": 90,
            "Semiannual": 182,
            "Annual": 365,
        }
        days = mapping.get(freq)
        if not days:
            return None
        return (last_dt + datetime.timedelta(days=days)).date()

    # Customers (ERPNext)
    add_rows_for("Customer", "name")

    # CRM Organization (CRM app)
    if frappe.db.exists("DocType", "CRM Organization"):
        add_rows_for("CRM Organization", "name")

    return cols, data
