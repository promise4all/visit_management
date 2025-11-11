import frappe

def execute():
    # Ensure roles exist
    for role_name in ("Field Sales Executive", "Sales Manager"):
        try:
            if not frappe.db.exists("Role", role_name):
                doc = frappe.get_doc({
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                })
                doc.insert(ignore_permissions=True)
        except Exception:
            # Best-effort role creation
            pass

    # Create Workflow for Visit to control approval lifecycle if not exists
    try:
        if not frappe.db.exists("Workflow", "Visit Approval"):
            wf = frappe.get_doc({
                "doctype": "Workflow",
                "workflow_name": "Visit Approval",
                "document_type": "Visit",
                "workflow_state_field": "workflow_state",
                "is_active": 1,
                "states": [
                    {
                        "state": "Draft",
                        "doc_status": 0,
                        "allow_edit": ", ".join(["Field Sales Executive", "Sales Manager"]),
                        "update_field": "workflow_state",
                    },
                    {
                        "state": "Pending Approval",
                        "doc_status": 0,
                        "allow_edit": ", ".join(["Field Sales Executive", "Sales Manager"]),
                        "update_field": "workflow_state",
                    },
                    {
                        "state": "Approved",
                        "doc_status": 0,
                        "allow_edit": "Sales Manager",
                        "update_field": "workflow_state",
                    },
                    {
                        "state": "Cancelled",
                        "doc_status": 0,
                        "allow_edit": "",
                        "update_field": "workflow_state",
                    },
                ],
                "transitions": [
                    {
                        "state": "Draft",
                        "action": "Send for Approval",
                        "next_state": "Pending Approval",
                        "allowed": "Field Sales Executive",
                    },
                    {
                        "state": "Pending Approval",
                        "action": "Approve",
                        "next_state": "Approved",
                        "allowed": "Sales Manager",
                    },
                    {
                        "state": "Pending Approval",
                        "action": "Cancel",
                        "next_state": "Cancelled",
                        "allowed": "Sales Manager",
                    },
                ],
            })
            wf.insert(ignore_permissions=True)
    except Exception:
        # Workflow creation is best-effort; admins can adjust via UI if needed
        pass
