# Copyright (c) 2025, Visit Management
# See license.txt

app_name = "visit_management"
app_title = "Visit Management"
app_publisher = "Promise Otigba"
app_description = "Backend Visit Management app integrated with Frappe CRM"
app_email = "ops@example.com"
app_license = "MIT"

# Keep frontend assets empty to avoid build issues (backend-only app)
# app_include_js = []
# app_include_css = []

# Required apps
# Ensure Frappe CRM (crm), HRMS (hrms) and ERPNext (erpnext) are installed
required_apps = ["crm", "hrms", "erpnext"]

# DocType Events: CRM Integration hooks
doc_events = {
    "Visit": {
        "validate": "visit_management.crm_integration.on_visit_validate",
        "on_update": "visit_management.crm_integration.on_visit_update",
        "after_insert": "visit_management.crm_integration.on_visit_after_insert",
        "on_trash": "visit_management.crm_integration.on_visit_trash",
    }
}

# Permissions hook pointing to the controller function
has_permission = {
    "Visit": "visit_management.visit_management.doctype.visit.visit.has_permission"
}

# Scheduler events for automation
scheduler_events = {
    "hourly": [],
    "daily": [
        "visit_management.tasks.cleanup_old_drafts",
        "visit_management.tasks.send_visit_reminders",
    ],
}

# Optional: expose a workspace config for integration into CRM workspace
workspace_config = [
    {
        "module_name": "Visits",
        "label": "Visits",
        "type": "module",
        "icon": "fa fa-map-marker",
        "links": [
            {"type": "DocType", "name": "Visit"},
            {"type": "DocType", "name": "Weekly Schedule"},
        ],
        "group": "FCRM",
        "is_hidden": 0,
    }
]

# Export these docs as fixtures when running `bench export-fixtures`
fixtures = [
    {"dt": "Workspace", "filters": [["module", "=", "Visit Management"]]},
    {"dt": "Number Card", "filters": [["module", "=", "Visit Management"]]},
    {"dt": "Dashboard", "filters": [["module", "=", "Visit Management"]]},
    {"dt": "Dashboard Chart", "filters": [["module", "=", "Visit Management"]]},
    {"dt": "Custom HTML Block", "filters": [["name", "=", "Visits KPI Panel"]]},
]

# Ensure workspace, number cards, chart, and custom HTML panel are present after install/migrate
after_install = "visit_management.utils.setup_visit_workspace_and_metrics"
after_migrate = [
    "visit_management.utils.setup_visit_workspace_and_metrics",
]
