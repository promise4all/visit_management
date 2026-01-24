import frappe


def execute():
    # Check if additional_notes field exists in Visit doctype
    if not frappe.db.has_column("Visit", "additional_notes"):
        # Field doesn't exist yet, skip migration
        # It will be created when the DocType updates run
        return
    
    # Move notes into additional_notes and clear the original notes
    try:
        visits = frappe.db.get_all(
            "Visit",
            fields=["name", "notes", "additional_notes"],
            filters={"notes": ["is", "set"]},
        )

        for doc in visits:
            if not doc.notes:
                continue

            new_additional = (doc.additional_notes or "").strip()
            if new_additional:
                new_additional = f"{new_additional}\n\n{doc.notes}".strip()
            else:
                new_additional = doc.notes

            frappe.db.set_value(
                "Visit",
                doc.name,
                {
                    "additional_notes": new_additional,
                    "notes": None,
                },
                update_modified=False,
            )

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error migrating notes to additional_notes: {e}", "Visit Migration")
        # Don't fail the entire migration for this patch
