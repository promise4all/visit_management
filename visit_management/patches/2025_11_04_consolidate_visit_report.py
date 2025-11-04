import frappe

def execute():
    """Migrate Visit Report data into Visit and remove workspace references.

    - Copies Visit Report.summary -> Visit.report_summary
    - Copies Visit Report.attachments -> Visit.report_attachment
    - Leaves Visit Report records intact (for audit); you may delete the DocType later if desired.
    """
    if not frappe.db.exists("DocType", "Visit"):
        return

    # Ensure target fields exist on Visit (skip migration if not yet applied)
    visit_meta = frappe.get_meta("Visit")
    if not (visit_meta.has_field("report_summary") and visit_meta.has_field("report_attachment")):
        # Fields not present yet; skip safely
        return

    if not frappe.db.exists("DocType", "Visit Report"):
        return

    moved = 0
    for vr in frappe.get_all("Visit Report", fields=["name", "visit", "summary", "attachments"], limit=100000):
        if not vr.get("visit"):
            continue
        try:
            v = frappe.get_doc("Visit", vr["visit"]) 
        except frappe.DoesNotExistError:
            continue
        # Only set if empty to avoid overwriting manual entries
        updates = {}
        if not v.get("report_summary") and vr.get("summary"):
            updates["report_summary"] = vr.get("summary")
        if not v.get("report_attachment") and vr.get("attachments"):
            updates["report_attachment"] = vr.get("attachments")
        if updates:
            v.db_set(updates, update_modified=False)
            moved += 1
    frappe.db.commit()
    frappe.clear_cache(doctype="Visit")
    # Optionally, you can remove the Visit Report shortcut from the Visits workspace if still present
    try:
        if frappe.db.exists("Workspace", "Visits"):
            ws = frappe.get_doc("Workspace", "Visits")
            # Remove Visit Report shortcut from child table
            if ws.get("shortcuts"):
                ws.set(
                    "shortcuts",
                    [row for row in ws.shortcuts if not (row.get("type") == "DocType" and row.get("link_to") == "Visit Report")],
                )
                ws.save(ignore_permissions=True)
    except Exception:
        pass

    frappe.logger().info(f"Consolidation patch moved data into Visit: {moved} records updated")
