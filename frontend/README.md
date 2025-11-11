# Visit Management Frontend Overrides for Frappe CRM

This folder contains a lightweight, optional src override for the CRM Vue frontend. It lets this app add routes and pages (Visits, Weekly Schedule) without modifying CRM business code.

- Overrides live under: `frontend/src-overrides/crm/src` and mirror CRM's `apps/crm/frontend/src`
- A small resolver plugin in CRM's `vite.config.js` prefers files from this folder when present
- If this folder is absent, CRM behaves normally

## Structure

- `src-overrides/crm/src/router.js` – overrides CRM router to add our routes
- `src-overrides/crm/src/pages/Visits.vue` – Visits list page
- `src-overrides/crm/src/pages/Visit.vue` – Visit detail with check-in/out buttons
- `src-overrides/crm/src/pages/WeeklySchedule.vue` – Placeholder schedule approvals screen
- `src-overrides/crm/src/composables/useVisits.js` – Data/composable for Visits
- `src-overrides/crm/src/composables/useWeeklySchedule.js` – Placeholder composable (wire backend methods later)

## Development

1. Start CRM frontend dev server (`apps/crm/frontend`): `yarn dev`
2. Navigate to:
   - `/crm/visits`
   - `/crm/visits/<visit-name>`
   - `/crm/weekly-schedule`

## Notes

- Check-in/out buttons call `run_doc_method` on the Visit doc (methods are whitelisted server-side)
- Weekly Schedule endpoints are placeholders – the UI won't auto-load until server methods are added
- You can add additional override roots by setting env `CRM_SRC_OVERRIDES` (comma separated paths)
