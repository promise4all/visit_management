# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-11-05

Initial public release of Visit Management.

- Consolidated Visit Report into Visit; Visit Report kept read-only for audit
- Visit Management Settings: enforce photo/geolocation, role exemptions, automation toggles
- Weekly Schedule with approval and auto-creation of Visits
- HRMS integration: check-in/out, attendance update, auto duration calculation
- Maintenance flow: mandatory details, auto-create ERPNext Maintenance Visit; manual "Create Maintenance Visit now" action
- KPIs: Number Cards (Planned, In Progress, Completed, Overdue), Dashboard Chart "Visits Created"
- Workspace "Visits" with Custom HTML Block "Visits KPI Panel"
- Robust install: minimal package.json (no Corepack), corrected fixtures, post-install/migrate upserts
- Dependencies documented (Frappe/ERPNext/HRMS v15; CRM unpinned branch-based)

