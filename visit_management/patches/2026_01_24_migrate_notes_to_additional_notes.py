import frappe


def execute():
    # Move notes into additional_notes and clear the original notes
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
