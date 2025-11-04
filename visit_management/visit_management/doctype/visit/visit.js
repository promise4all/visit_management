frappe.ui.form.on('Visit', {
  onload(frm) {
    // Default Assigned To to current user when creating a new document
    if (frm.is_new() && !frm.doc.assigned_to) {
      frm.set_value('assigned_to', frappe.session.user);
    }

    // If location is empty, try to capture current geolocation (best effort)
    if (frm.is_new() && !frm.doc.location && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords || {};
          if (latitude && longitude) {
            frm.set_value('location', { lat: latitude, lng: longitude });
          }
        },
        () => {/* ignore */},
        { enableHighAccuracy: true, maximumAge: 60000, timeout: 8000 }
      );
    }
  },

  refresh(frm) {
    // Show a convenient button to create MV when eligible
    const isMaintenance = (frm.doc.subject || '').toLowerCase() === 'maintenance';
    const canCreateMV = isMaintenance && frm.doc.client_type === 'Customer' && frm.doc.status === 'Completed' && !frm.doc.maintenance_visit;
    if (canCreateMV) {
      frm.add_custom_button(__('Create Maintenance Visit'), async () => {
        try {
          await ensure_saved(frm);
          const r = await frm.call('create_maintenance_visit_now');
          if (r && r.message) {
            frappe.msgprint({
              title: __('Maintenance Visit Created'),
              message: __('Linked Maintenance Visit: {0}', [
                `<a href="#Form/Maintenance%20Visit/${r.message}">${r.message}</a>`
              ]),
              indicator: 'green',
            });
            await frm.reload_doc();
          }
        } catch (e) {
          // feedback already given by server
        }
      }, __('Actions'));
    }
  },

  client_type(frm) {
    // Clear client and address when type changes
    frm.set_value('client', null);
    frm.set_value('address', null);
  },

  client(frm) {
    // Fetch default address from server when client changes
    if (frm.doc.client_type && frm.doc.client) {
      frm.call('get_client_default_address', {
        client_type: frm.doc.client_type,
        client: frm.doc.client,
      }).then(r => {
        if (r && r.message) {
          frm.set_value('address', r.message);
        }
      });
    } else {
      frm.set_value('address', null);
    }
  },

  async check_in(frm) {
    await ensure_saved(frm);
    await capture_and_attach(frm, 'check_in_photo');
    await frm.call('check_in');
    await frm.reload_doc();
  },
  async check_out(frm) {
    await ensure_saved(frm);
    await capture_and_attach(frm, 'check_out_photo');
    await frm.call('check_out');
    await frm.reload_doc();
  },
});

async function ensure_saved(frm) {
  if (frm.is_new() || frm.is_dirty()) {
    await frm.save();
  }
}

async function capture_and_attach(frm, fieldname) {
  const file = await capture_from_camera();
  if (!file) {
    frappe.throw('Camera capture is required.');
  }
  const dataUrl = await file_to_dataurl(file);
  const filename = `${fieldname}-${frappe.datetime.now_datetime().replace(/\s|:|\./g, '-')}.jpg`;
  const r = await frappe.call({
    method: 'frappe.client.uploadfile',
    args: {
      filename,
      filedata: dataUrl,
      doctype: frm.doc.doctype,
      docname: frm.doc.name,
      fieldname,
    },
  });
  if (r && r.message && r.message.file_url) {
    await frm.set_value(fieldname, r.message.file_url);
  }
}

function capture_from_camera() {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.onchange = () => resolve(input.files && input.files[0]);
    input.click();
  });
}

function file_to_dataurl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
