# Visit Management (Frappe)

Comprehensive Visit Management app for Frappe/ERPNext with full CRM integration. Provides DocTypes, server logic, Vue frontend components, and automation for field visits, check-ins/check-outs with photo capture, geolocation tracking, and detailed visit reporting.

- Compatible with Frappe v15+, CRM Module, HRMS
- Full Frontend: Vue.js components with Frappe UI integration
- Backend: DocTypes, Hooks, Scheduler, Fixtures, API endpoints

## Features

### Core Visit Management
- **Visit DocType** with comprehensive fields:
  - Client Management: Client Type (Lead/Deal/Organization/Customer), Client link, Contact
  - Purpose: Sales Call, Follow-up, Demo, Maintenance, Collection, Inspection
  - Scheduling: Scheduled Time, Auto-calculated Duration
  - Check-in/Check-out with:
    - Photo Capture (base64 attachment to private files)
    - GPS Geolocation (Latitude/Longitude)
    - Automatic Check-in Time recording
    - Employee Checkin integration (HRMS)
    - Attendance auto-sync

### Visit Reporting & Outcomes
- Visit Outcome tracking (Successful/Unsuccessful/Follow-up Required)
- Comprehensive Report Section:
  - Competitor Information
  - Existing Fleet Information
  - Requirements Received
  - Future Prospects
  - Potential Product Target
  - Customer Feedback
  - Report Attachment (file upload)
  - Additional Notes
- Activity Log showing Check-in/Check-out timeline with user tracking
- Status-based automation (Planned → In Progress → Completed → Auto-submit)

### Maintenance Workflow
- Maintenance-specific fields (Support Issue, Maintenance Details, Work Done)
- Auto-creates ERPNext Maintenance Visit on completion
- Links to Serial No and Item for tracked maintenance items

### Weekly Schedule
- Plan visits by week with day/time/client/contact/purpose
- Manager approval workflow
- Auto-generate planned Visits from approved rows

### Photo & Location Handling
- Base64 photo encoding/decoding with automatic file attachment
- Private file storage (is_private=1) for security
- Duplicate photo cleanup on check-in/check-out retries
- GPS location capture with text-format storage (Latitude/Longitude)
- Embedded Google Maps visualization on detail page

### Frontend (CRM Integration)
- **Visit List View**: Modal-based interface matching CRM pattern
  - Row click opens VisitDetailModal with quick summary
  - "View Full Details" routes to comprehensive detail page
- **Visit Detail Page** (`/crm/visits/:visitId`):
  - Organized sections: Client Info, Visit Details, Activity, Photos, Location, Report, Activity Log
  - Dynamic field rendering for all populated fields
  - Photo gallery with hover effects
  - Embedded Google Maps showing check-in/check-out locations
  - Check-in/Check-out buttons with photo + location capture
  - Status dropdown with color indicators
  - Responsive design (mobile-first)

### Database Migrations
- Migration patch to consolidate notes into additional_notes field
- Automatic execution on deploy via patches.txt
- Data preservation with optional merging of existing content

### Settings & Configuration
- Toggle photo requirements (check-in/check-out)
- Toggle geolocation requirements
- Check-in exemption by role
- Auto-submission on completion behavior

## Install

1) From a bench, add the repo and install the app:

```bash
bench get-app visit_management https://github.com/promise4all/visit_management.git
bench --site <site-name> install-app visit_management
```

2) Ensure required apps are installed first:

```bash
# Required apps (specified in hooks):
frappe
erpnext
hrms
crm
```

3) Build frontend assets:

```bash
bench build --app visit_management
```

## Development

- Export fixtures (workspaces, charts, cards, etc.):

```bash
bench export-fixtures
```

- Run migrations and reload metadata:

```bash
bench migrate
```

- Build frontend assets:

```bash
cd apps/visit_management/frontend
yarn install
yarn build
# Or from bench root:
bench build --app visit_management
```

## Architecture

### Backend (`visit_management/`)
- `doctype/visit/visit.py`: Core Visit document controller with:
  - `check_in()`: Photo attachment, location capture, Employee Checkin creation
  - `check_out()`: Photo attachment, location capture, duration calculation
  - `create_maintenance_visit_now()`: On-demand Maintenance Visit creation
  - Auto-submit on Completed status
  - Photo field hydration from File attachments

### Frontend (`frontend/src-overrides/crm/src/`)
- `pages/Visits.vue`: List view with modal trigger
- `pages/Visit.vue`: Detail page with:
  - Dynamic field rendering
  - Photo gallery display
  - Location map (Google Maps embed)
  - Activity log table
  - Report section rendering
  - Check-in/Check-out functionality
- `components/Modals/VisitDetailModal.vue`: Quick view modal
- `composables/useVisits.js`: Resource management for list and detail views

### Data Flow
1. User clicks visit row → `onRowClick` handler opens modal
2. Modal fetches visit with `frappe.client.get`
3. "View Full Details" routes to `/crm/visits/:visitId?mode=details`
4. Detail page displays all fields with dynamic rendering
5. Photos stored as file URLs (not JSON arrays)
6. Locations stored as text format: `"Latitude: X, Longitude: Y"`

## Packaging & Dependencies

- PEP 621 project configuration (`pyproject.toml`) with Flit
- Version in `visit_management/__init__.py`
- Source data files (`*.json`) included via `MANIFEST.in`
- Required apps via Bench: Frappe v15, ERPNext v15, HRMS v15, CRM
- Frontend: Vue 3, Frappe UI components, Vite build system

Build a distribution:

```bash
python -m build  # or: flit build
```

## License

MIT
