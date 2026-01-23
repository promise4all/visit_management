frappe.ui.form.on('Visit', {
  onload(frm) {
    // Set up dynamic filtering for Contact field based on client_type and client
    frm.set_query('contact', () => {
      if (!frm.doc.client_type || !frm.doc.client) {
        return {
          filters: {
            name: ['=', ''], // No results if client not selected
          }
        };
      }
      return {
        query: 'visit_management.visit_management.doctype.visit.visit.get_contact_query',
        filters: {
          client_type: frm.doc.client_type,
          client: frm.doc.client,
        }
      };
    });

    // Set up dynamic filtering for Address field based on client_type and client
    frm.set_query('address', () => {
      if (!frm.doc.client_type || !frm.doc.client) {
        return {
          filters: {
            name: ['=', ''], // No results if client not selected
          }
        };
      }
      return {
        query: 'visit_management.visit_management.doctype.visit.visit.get_address_query',
        filters: {
          client_type: frm.doc.client_type,
          client: frm.doc.client,
        }
      };
    });

    // Default Assigned To to current user when creating a new document
    if (frm.is_new() && !frm.doc.assigned_to) {
      frm.set_value('assigned_to', frappe.session.user);
    }
  },

  refresh(frm) {
    // Render the dual-marker map if attendance section is visible
    if (frm.doc.check_in_time || frm.doc.check_out_time) {
      render_visit_locations_map(frm);
    }
    
    // Render photo previews
    render_photo_preview(frm, 'check_in_photo_preview', frm.doc.check_in_photo);
    render_photo_preview(frm, 'check_out_photo_preview', frm.doc.check_out_photo);
    
    // Add Check-in button if not checked in yet
    if (!frm.doc.check_in_time && frm.doc.status !== 'Cancelled') {
      const btn = frm.add_custom_button(__('Check In'), async () => {
        await ensure_saved(frm);
        // Capture photo and location, then send to server in a single call to avoid version conflicts
        const photo = await capture_photo_base64('check_in_photo');
        const location = await get_current_location();
        await frm.call({ method: 'check_in', doc: frm.doc, args: { location, photo_data: photo?.base64 || null, photo_filename: photo?.filename || null } });
        await frm.reload_doc();
        frappe.show_alert({message: __('Checked in successfully'), indicator: 'green'});
      }, __('Actions'));
      if (btn) btn.addClass('btn-primary');
    }
    
    // Add Check-out button only if checked in and not checked out
    if (frm.doc.check_in_time && !frm.doc.check_out_time && frm.doc.status !== 'Cancelled') {
      const btn = frm.add_custom_button(__('Check Out'), async () => {
        await ensure_saved(frm);
        const photo = await capture_photo_base64('check_out_photo');
        const location = await get_current_location();
        await frm.call({ method: 'check_out', doc: frm.doc, args: { location, photo_data: photo?.base64 || null, photo_filename: photo?.filename || null } });
        await frm.reload_doc();
        frappe.show_alert({message: __('Checked out successfully'), indicator: 'green'});
      }, __('Actions'));
      if (btn) btn.addClass('btn-primary');
    }

    // Ensure cancel remains accessible even if core toolbar actions are altered elsewhere
    if (frm.doc.docstatus === 1 && frm.doc.status !== 'Cancelled' && frm.perm?.[0]?.cancel) {
      frm.add_custom_button(__('Cancel'), () => frm.cancel_doc(), __('Actions'));
    }
    
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
    // Clear client, contact, and address when type changes
    frm.set_value('client', null);
    frm.set_value('contact', null);
    frm.set_value('address', null);
  },

  client(frm) {
    // Clear contact and address when client changes (needs reselection after client change)
    frm.set_value('contact', null);
    frm.set_value('address', null);
    
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
    }
  },

  contact(frm) {
    // Auto-fetch contact details when contact is selected
    if (frm.doc.contact) {
      frappe.db.get_value('Contact', frm.doc.contact, ['email_id', 'phone', 'mobile_no', 'designation'])
        .then(r => {
          if (r && r.message) {
            frm.set_value('contact_email', r.message.email_id);
            frm.set_value('contact_phone', r.message.phone);
            frm.set_value('contact_mobile', r.message.mobile_no);
            frm.set_value('contact_designation', r.message.designation);
          }
        });
    } else {
      // Clear contact details if contact is cleared
      frm.set_value('contact_email', null);
      frm.set_value('contact_phone', null);
      frm.set_value('contact_mobile', null);
      frm.set_value('contact_designation', null);
    }
  },

  async check_in(frm) {
    await ensure_saved(frm);
    const photo = await capture_photo_base64('check_in_photo');
    const location = await get_current_location();
    await frm.call({ method: 'check_in', doc: frm.doc, args: { location, photo_data: photo?.base64 || null, photo_filename: photo?.filename || null } });
    await frm.reload_doc();
  },
  async check_out(frm) {
    await ensure_saved(frm);
    const photo = await capture_photo_base64('check_out_photo');
    const location = await get_current_location();
    await frm.call({ method: 'check_out', doc: frm.doc, args: { location, photo_data: photo?.base64 || null, photo_filename: photo?.filename || null } });
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
  // Strip the data URL prefix; fall back to full string if no comma is present
  const base64Data = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl;
  const filename = `${fieldname}-${frappe.datetime.now_datetime().replace(/\s|:|\./g, '-')}.jpg`;
  const r = await frappe.call({
    method: 'visit_management.visit_management.api.attach_visit_photo',
    args: {
      filename,
      filedata: base64Data,
      doctype: frm.doc.doctype,
      docname: frm.doc.name,
      fieldname,
      is_private: 0,
    },
  });
  // Server helper already sets the field value; avoid client-side set_value to prevent version conflicts
}

// New: capture a photo and return filename + base64 (no server mutation here)
async function capture_photo_base64(fieldname) {
  const file = await capture_from_camera();
  if (!file) {
    frappe.throw('Camera capture is required.');
  }
  const dataUrl = await file_to_dataurl(file);
  const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl;
  const filename = `${fieldname}-${frappe.datetime.now_datetime().replace(/\s|:|\./g, '-')}.jpg`;
  return { filename, base64 };
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
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function get_current_location() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      frappe.msgprint('Geolocation is not supported by your browser');
      resolve(null);
      return;
    }
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        });
      },
      (error) => {
        console.error('Error getting location:', error);
        frappe.msgprint('Could not get location: ' + error.message);
        resolve(null);
      }
    );
  });
}

function render_visit_locations_map(frm) {
  const container = frm.fields_dict.locations_map.$wrapper;
  if (!container || !container.length) return;
  
  container.empty();
  
  let check_in_loc = null;
  let check_out_loc = null;
  
  // Parse check-in location from text format "Latitude: X, Longitude: Y"
  if (frm.doc.check_in_location) {
    try {
      const match = frm.doc.check_in_location.match(/Latitude:\s*([-\d.]+),\s*Longitude:\s*([-\d.]+)/);
      if (match) {
        check_in_loc = { lat: parseFloat(match[1]), lng: parseFloat(match[2]) };
      }
    } catch (e) {
      console.error('Error parsing check_in_location:', e);
    }
  }
  
  // Parse check-out location from text format
  if (frm.doc.check_out_location) {
    try {
      const match = frm.doc.check_out_location.match(/Latitude:\s*([-\d.]+),\s*Longitude:\s*([-\d.]+)/);
      if (match) {
        check_out_loc = { lat: parseFloat(match[1]), lng: parseFloat(match[2]) };
      }
    } catch (e) {
      console.error('Error parsing check_out_location:', e);
    }
  }
  
  // If no locations, show placeholder
  if (!check_in_loc && !check_out_loc) {
    container.html('<div style="padding: 20px; text-align: center; color: #999;">No location data available yet</div>');
    return;
  }
  
  // Create map container
  const mapDiv = $('<div id="visit_map" style="height: 400px; width: 100%; border-radius: 4px;"></div>');
  container.append(mapDiv);
  
  // Wait for Leaflet to be available
  frappe.require('/assets/frappe/node_modules/leaflet/dist/leaflet.css');
  frappe.require('/assets/frappe/node_modules/leaflet/dist/leaflet.js', () => {
    const L = window.L;
    
    // Determine center and zoom
    let center = check_in_loc || check_out_loc;
    let zoom = 15;
    
    // If both locations exist, calculate center between them
    if (check_in_loc && check_out_loc) {
      center = {
        lat: (check_in_loc.lat + check_out_loc.lat) / 2,
        lng: (check_in_loc.lng + check_out_loc.lng) / 2
      };
    }
    
    // Create map
    const map = L.map('visit_map').setView([center.lat, center.lng], zoom);
    
    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Create custom icons
    const checkInIcon = L.divIcon({
      className: 'custom-marker',
      html: '<div style="background-color: #22c55e; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
      iconSize: [30, 30],
      iconAnchor: [15, 15]
    });
    
    const checkOutIcon = L.divIcon({
      className: 'custom-marker',
      html: '<div style="background-color: #ef4444; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
      iconSize: [30, 30],
      iconAnchor: [15, 15]
    });
    
    // Add check-in marker
    if (check_in_loc && check_in_loc.lat && check_in_loc.lng) {
      const checkInMarker = L.marker([check_in_loc.lat, check_in_loc.lng], { icon: checkInIcon }).addTo(map);
      checkInMarker.bindPopup('<b>Check-in Location</b><br>' + frm.doc.check_in_time + '<br>' + frm.doc.check_in_location);
    }
    
    // Add check-out marker
    if (check_out_loc && check_out_loc.lat && check_out_loc.lng) {
      const checkOutMarker = L.marker([check_out_loc.lat, check_out_loc.lng], { icon: checkOutIcon }).addTo(map);
      checkOutMarker.bindPopup('<b>Check-out Location</b><br>' + frm.doc.check_out_time + '<br>' + frm.doc.check_out_location);
    }
    
    // If both markers exist, fit bounds to show both
    if (check_in_loc && check_out_loc && check_in_loc.lat && check_out_loc.lat) {
      const bounds = L.latLngBounds(
        [check_in_loc.lat, check_in_loc.lng],
        [check_out_loc.lat, check_out_loc.lng]
      );
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  });
}

function render_photo_preview(frm, preview_field, photo_url) {
  const container = frm.fields_dict[preview_field].$wrapper;
  if (!container || !container.length) return;
  
  container.empty();
  
  if (photo_url) {
    const img = $(`
      <div style="text-align: center;">
        <img src="${photo_url}" 
             style="max-width: 100%; max-height: 300px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
             alt="Photo preview">
      </div>
    `);
    container.append(img);
  } else {
    const placeholder = $(`
      <div style="padding: 40px; text-align: center; color: #999; border: 2px dashed #ddd; border-radius: 4px;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="margin-bottom: 10px;">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
        <div>No photo captured yet</div>
      </div>
    `);
    container.append(placeholder);
  }
}
