# Visit Management (Frappe)

Backend-only Visit Management app for Frappe/ERPNext. Provides DocTypes, server logic, and automation for field visits and weekly planning—no custom web assets required.

- Compatible with Frappe v15+
- Scope: Backend (DocTypes, Hooks, Scheduler, Fixtures)

## Features
- Visit (single DocType) with:
	- Purpose (Select), Client (Lead/Deal/Organization/Customer)
	- Check-in/Check-out with optional photos and geolocation (via settings)
	- Auto-calculated visit duration
	- Completion-only reporting fields
	- Maintenance flow: requires details; on completion, auto-creates and links ERPNext Maintenance Visit if Support Issue isn’t provided
- Weekly Schedule:
	- Child rows: day/time/client/contact/purpose/notes; manager approvals
	- Approve rows and auto-create planned Visits (server RPC + form buttons)
- Settings (singleton): toggles for photos/geolocation/check-in exemption, auto-create behavior, etc.
- Workspace KPIs/Charts/Number Cards as fixtures (optional)

## Install

1) From a bench, add the repo and install the app:

```bash
bench get-app visit_management https://github.com/promise4all/visit_management.git
bench --site <site-name> install-app visit_management
```

2) Ensure required apps are installed first (hooks specify):

```text
required_apps = ["crm", "hrms", "erpnext"]
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

## Packaging & dependencies

- This app uses `pyproject.toml` (PEP 621) with Flit for builds.
- Version is defined in `visit_management/__init__.py` (`__version__`).
- Source data files (`*.json`) are included via `MANIFEST.in`.
- Bench-managed app dependencies: Frappe v15, ERPNext v15, and HRMS v15 must be installed on the bench (documented in `pyproject.toml` under optional dependencies, but installed via Bench).
- A minimal `package.json` is included to satisfy Node tooling; no custom web assets are built for this app.

Build a distribution:

```bash
python -m build  # or: flit build
```

## License

MIT
