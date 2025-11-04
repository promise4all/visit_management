frappe.ui.form.on('Weekly Schedule', {
    onload(frm) {
        if (frm.is_new() && (!frm.doc.details || frm.doc.details.length === 0)) {
            const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
            days.forEach(d => {
                frm.add_child('details', { day: d });
            });
            frm.refresh_field('details');
        }
    },
    refresh(frm) {
        const is_manager = frappe.user.has_role('Sales Manager') || frappe.user.has_role('System Manager');

        // helper to get selected child rows in the grid
        const get_selected = () => (frm.fields_dict.details?.grid?.get_selected_children?.() || []);

        if (is_manager) {
            frm.add_custom_button('Approve Selected', () => {
                const selected = get_selected();
                if (!selected.length) {
                    frappe.msgprint('Select one or more rows in Details first.');
                    return;
                }
                frappe.call({
                    method: 'visit_management.visit_management.doctype.weekly_schedule.weekly_schedule.approve_rows',
                    args: {
                        schedule: frm.doc.name,
                        rows: selected.map(r => r.name)
                    },
                    freeze: true,
                    freeze_message: 'Approving selected rows...'
                }).then(r => {
                    const data = r?.message || {};
                    frappe.show_alert({message: `Approved ${data.approved || 0} rows. Created ${data.created?.length || 0} visits.`, indicator: 'green'});
                    frm.reload_doc();
                });
            });

            frm.add_custom_button('Create Visits for Approved', () => {
                frappe.call({
                    method: 'visit_management.visit_management.doctype.weekly_schedule.weekly_schedule.create_visits_for_approved_rows',
                    args: { schedule: frm.doc.name },
                    freeze: true,
                    freeze_message: 'Creating visits...'
                }).then(r => {
                    const data = r?.message || {};
                    frappe.show_alert({message: `Created ${data.created?.length || 0} visits.`, indicator: 'green'});
                    frm.reload_doc();
                });
            });
        }

        if (frm.doc.status === 'Draft') {
            frm.add_custom_button('Submit for Approval', () => {
                frm.set_value('status', 'Pending Approval');
                frm.save();
            }, 'Actions');
        }
    }
});
