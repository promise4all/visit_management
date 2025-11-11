import frappe

def execute():
    # Remove the Visit workflow we added earlier if it exists; Weekly Schedule will own approvals
    try:
        if frappe.db.exists("Workflow", "Visit Approval"):
            frappe.delete_doc("Workflow", "Visit Approval", ignore_permissions=True)
    except Exception:
        pass
