from __future__ import annotations

import frappe
from frappe import whitelist
from frappe.modules.import_file import import_file_by_path
from frappe.utils import (
    now_datetime,
    getdate,
    get_first_day,
    get_last_day,
    get_first_day_of_week,
    get_last_day_of_week,
    get_quarter_start,
    get_quarter_ending,
    get_year_start,
    get_year_ending,
)


@whitelist()
def debug_doctypes_presence():
    names = [
        "Visit",
        "Weekly Schedule",
        "Visit Log",
        "Visit Photo",
        "Weekly Schedule Detail",
    ]
    out = {n: bool(frappe.db.exists("DocType", n)) for n in names}
    return out


@whitelist()
def sync_all_visit_doctypes(force: int = 1):
    """Force-import this app's DocTypes from JSON files.

    This is a fallback when migrate didn't pick them up (e.g., unusual bench state).
    """
    doctypes = [
        ("visit", "visit.json"),
        ("weekly_schedule", "weekly_schedule.json"),
        ("visit_log", "visit_log.json"),
        ("visit_photo", "visit_photo.json"),
        ("weekly_schedule_detail", "weekly_schedule_detail.json"),
    ]
    results = {}
    import os
    import importlib
    # Resolve the deep Studio-style doctype package path dynamically
    # visit_management.visit_management.doctype
    doctype_pkg = importlib.import_module("visit_management.visit_management.doctype")
    base_doctype_path = os.path.dirname(doctype_pkg.__file__)
    for folder, fname in doctypes:
        path = os.path.join(base_doctype_path, folder, fname)
        exists = os.path.exists(path)
        try:
            import_file_by_path(path, force=bool(force))
            results[folder] = {"imported": True, "path": path, "exists": exists}
        except Exception as e:
            results[folder] = {"imported": False, "path": path, "exists": exists, "error": str(e)}
    frappe.clear_cache()
    return results


@whitelist()
def check_imports():
    """Debug python import paths for doctype modules."""
    out = {}
    modules = [
        "visit_management",
        "visit_management.visit_management",
        "visit_management.visit_management.doctype",
        "visit_management.visit_management.doctype.visit_log",
        "visit_management.visit_management.doctype.visit_photo",
        "visit_management.visit_management.doctype.weekly_schedule_detail",
        "visit_management.visit_management.doctype.weekly_schedule",
        "visit_management.visit_management.doctype.visit",
    # "visit_management.visit_management.doctype.visit_report",  # consolidated into Visit
        # Deep path variants (should also exist physically)
        "visit_management.visit_management.visit_management",
        "visit_management.visit_management.visit_management.doctype",
        "visit_management.visit_management.visit_management.doctype.visit",
    ]
    for m in modules:
        try:
            __import__(m)
            out[m] = True
        except Exception as e:
            out[m] = f"error: {e}"
    try:
        import sys
        out["sys_has_vm_vm_doctype"] = "visit_management.visit_management.doctype" in sys.modules
    except Exception:
        pass
    # Inspect doctype package path and listdir
    try:
        import importlib, os
        pkg = importlib.import_module("visit_management.visit_management.doctype")
        pkg_path = os.path.dirname(pkg.__file__)
        out["doctype_pkg_path"] = pkg_path
        out["doctype_pkg_listdir"] = sorted(os.listdir(pkg_path))
        # show which subpackages contain __init__.py
        inits = {}
        for name in [
            "visit",
            "visit_log",
            "visit_photo",
            # "visit_report",
            "weekly_schedule",
            "weekly_schedule_detail",
        ]:
            p = os.path.join(pkg_path, name, "__init__.py")
            inits[name] = os.path.exists(p)
        out["doctype_subpkg_inits"] = inits
    except Exception as e:
        out["doctype_pkg_error"] = str(e)
    return out


@whitelist()
def setup_visit_workspace_and_metrics():
    """Create Workspace, Number Cards, Dashboard, and Chart for Visits if missing."""
    # Number Cards
    cards = [
        {
            "name": "Planned Visits",
            "label": "Planned Visits",
            "filters_json": "[[\"Visit\",\"status\",\"=\",\"Planned\"]]",
        },
        {
            "name": "In Progress Visits",
            "label": "In Progress Visits",
            "filters_json": "[[\"Visit\",\"status\",\"=\",\"In Progress\"]]",
        },
        {
            "name": "Completed Visits",
            "label": "Completed Visits",
            "filters_json": "[[\"Visit\",\"status\",\"=\",\"Completed\"]]",
        },
        {
            "name": "Overdue Visits",
            "label": "Overdue Visits",
            # Static part: only planned / in progress
            "filters_json": "[[\"Visit\",\"status\",\"in\",[\"Planned\",\"In Progress\"]]]",
        },
    ]

    # Dynamic filters applied at runtime in browser (agent + month-to-date window)
    # Note: dynamic filters support any operator; values are JS expressions evaluated on client
    common_dynamic_filters = [
        ["Visit", "assigned_to", "=", "frappe.session.user"],
        ["Visit", "scheduled_time", ">=", "frappe.datetime.month_start()"],
        ["Visit", "scheduled_time", "<=", "frappe.datetime.now_datetime()"],
    ]

    overdue_dynamic_filters = [
        ["Visit", "assigned_to", "=", "frappe.session.user"],
        ["Visit", "scheduled_time", "<", "frappe.datetime.now_datetime()"],
    ]

    for c in cards:
        if not frappe.db.exists("Number Card", c["name"]):
            doc = frappe.get_doc({
                "doctype": "Number Card",
                "name": c["name"],
                "label": c["label"],
                "module": "Visit Management",
                "document_type": "Visit",
                "type": "Document Type",
                "function": "Count",
                "filters_json": c["filters_json"],
                "dynamic_filters_json": frappe.as_json(
                    overdue_dynamic_filters if c["name"] == "Overdue Visits" else common_dynamic_filters
                ),
                "is_standard": 1,
                "is_public": 1,
                "show_percentage_stats": 1,
                "stats_time_interval": "Daily",
            })
            doc.insert(ignore_permissions=True)
        else:
            # If a standard doc already exists, don't edit it to avoid validation errors.
            try:
                doc = frappe.get_doc("Number Card", c["name"])
                if int(doc.get("is_standard") or 0) != 1:
                    doc.update({
                        "label": c["label"],
                        "module": "Visit Management",
                        "document_type": "Visit",
                        "type": "Document Type",
                        "function": "Count",
                        "filters_json": c["filters_json"],
                        "dynamic_filters_json": frappe.as_json(
                            overdue_dynamic_filters if c["name"] == "Overdue Visits" else common_dynamic_filters
                        ),
                        "show_percentage_stats": 1,
                        "stats_time_interval": "Daily",
                    })
                    doc.save(ignore_permissions=True)
            except Exception:
                # best-effort; skip on validation issues
                pass

    # Dashboard Chart: Visits Created
    chart_name = "Visits Created"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        chart = frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": chart_name,
            "module": "Visit Management",
            "document_type": "Visit",
            "based_on": "creation",
            "chart_type": "Count",
            "type": "Bar",
            "timeseries": 1,
            "timespan": "Last Month",
            "time_interval": "Daily",
            "is_standard": 1,
            "is_public": 1,
            "filters_json": "[]",
            "dynamic_filters_json": frappe.as_json([["Visit", "assigned_to", "=", "frappe.session.user"]]),
            # important: ensure values are treated as plain numbers, not currency
            "currency": "",
        })
        chart.insert(ignore_permissions=True)
    else:
        # Avoid editing standard charts; only update if not marked standard
        try:
            chart = frappe.get_doc("Dashboard Chart", chart_name)
            if int(chart.get("is_standard") or 0) != 1:
                chart.update({
                    "document_type": "Visit",
                    "based_on": "creation",
                    "chart_type": "Count",
                    "type": "Bar",
                    "timeseries": 1,
                    "timespan": "Last Month",
                    "time_interval": "Daily",
                    "filters_json": "[]",
                    "dynamic_filters_json": frappe.as_json([["Visit", "assigned_to", "=", "frappe.session.user"]]),
                    # remove any accidental currency so tooltip shows numbers
                    "currency": "",
                })
                chart.save(ignore_permissions=True)
        except Exception:
            pass

    # Dashboard
    dash_name = "Visit Overview"
    if not frappe.db.exists("Dashboard", dash_name):
        dash = frappe.get_doc({
            "doctype": "Dashboard",
            "dashboard_name": dash_name,
            "module": "Visit Management",
            "is_standard": 1,
            "cards": [
                {"card": "Planned Visits"},
                {"card": "In Progress Visits"},
                {"card": "Completed Visits"},
            ],
            "charts": [
                {"chart": "Visits Created", "width": "Full"},
            ],
        })
        dash.insert(ignore_permissions=True)

    # Ensure client custom fields and frequency-overdue number card exist early
    try:
        _upsert_custom_fields_for_clients()
        _upsert_frequency_overdue_number_card()
    except Exception:
        pass

    # Workspace
    ws_name = "Visits"
    # Remove the older number-card widgets in the workspace content; keep panel + chart + a single frequency-overdue card + shortcuts
    workspace_content = (
        "[{\"id\":\"hdr1\",\"type\":\"header\",\"data\":{\"text\":\"<span class=\\\"h5\\\"><b>VISITS</b></span>\",\"col\":12}},{\"id\":\"sp1\",\"type\":\"spacer\",\"data\":{\"col\":12}},{\"id\":\"cb1\",\"type\":\"custom_block\",\"data\":{\"custom_block_name\":\"Visits KPI Panel\",\"col\":12}},{\"id\":\"sp1a\",\"type\":\"spacer\",\"data\":{\"col\":12}},{\"id\":\"ch1\",\"type\":\"chart\",\"data\":{\"chart_name\":\"Visits Created\",\"col\":12}},{\"id\":\"sp1b\",\"type\":\"spacer\",\"data\":{\"col\":12}},{\"id\":\"ncF\",\"type\":\"number_card\",\"data\":{\"number_card_name\":\"Overdue Routine Visits\",\"col\":3}},{\"id\":\"sp2\",\"type\":\"spacer\",\"data\":{\"col\":12}},{\"id\":\"p1\",\"type\":\"paragraph\",\"data\":{\"text\":\"<b>SHORTCUTS</b>\",\"col\":12}},{\"id\":\"sh1\",\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"Visit\",\"col\":3}},{\"id\":\"sh3\",\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"Weekly Schedule\",\"col\":3}},{\"id\":\"sh4\",\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"Visit Overview\",\"col\":3}}]"
    )
    workspace_shortcuts = [
        {"type": "DocType", "label": "Visit", "link_to": "Visit", "doc_view": "List", "color": "Grey", "stats_filter": "[]"},
        {"type": "DocType", "label": "Weekly Schedule", "link_to": "Weekly Schedule", "doc_view": "List", "color": "Grey", "stats_filter": "[]"},
        {"type": "Dashboard", "label": "Visit Overview", "link_to": "Visit Overview", "color": "Grey"},
    ]
    # Replace older number cards with a single frequency-overdue card (created above)
    workspace_cards = [{"label": "Overdue Routine Visits", "number_card_name": "Overdue Routine Visits"}]
    # Ensure Custom HTML Block exists for dynamic KPIs
    chb_name = "Visits KPI Panel"
    try:
        # Prefer importing from bundled JSON; if that fails, upsert programmatically
        import os, json
        from frappe import get_app_path
        chb_path = os.path.join(
            get_app_path("visit_management"),
            "visit_management",
            "custom_html_block",
            "visits_kpi_panel",
            "visits_kpi_panel.json",
        )
        html = script = style = None
        if os.path.exists(chb_path):
            try:
                with open(chb_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    html = data.get("html")
                    script = data.get("script")
                    style = data.get("style")
            except Exception:
                # fallback to import_file_by_path if json.load fails
                import_file_by_path(chb_path, force=True)
        # If JSON parsing failed or fields missing, fall back to embedded defaults
        if not (html and script is not None and style is not None):
            html = html or (
                """
<div class="vm-kpi-panel">
    <div class="vm-kpi-toolbar">
        <div class="left d-flex align-items-center">
            <div class="btn-group btn-group-sm mr-2">
                <button type="button" class="btn btn-default vm-mode-btn active" data-mode="my">My</button>
                <button type="button" class="btn btn-default vm-mode-btn" data-mode="team">Team</button>
            </div>
            <div class="vm-agent d-none">
                <label class="mr-2 text-muted">Agent</label>
                <select class="form-control input-sm vm-agent-select"><option value="">All</option></select>
            </div>
        </div>
        <div class="right d-flex align-items-center">
            <div class="vm-period mr-2">
                <label class="mr-2 text-muted">Period</label>
                <select class="form-control input-sm vm-period-select">
                    <option value="today">Today</option>
                    <option value="week">This Week</option>
                    <option value="month" selected> This Month</option>
                    <option value="quarter">This Quarter</option>
                    <option value="year">This Year</option>
                </select>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input vm-overdue-scope" type="checkbox" id="vmOverdueScope">
                <label class="form-check-label" for="vmOverdueScope">Overdue within period</label>
            </div>
            <span class="vm-role-hint badge badge-warning ml-2 d-none">Limited to My</span>
        </div>
    </div>
    <div class="vm-kpis row">
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card planned">
                <div class="kpi-label">Planned</div>
                <div class="kpi-value" data-key="planned">–</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card in-progress">
                <div class="kpi-label">In Progress</div>
                <div class="kpi-value" data-key="in_progress">–</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card completed">
                <div class="kpi-label">Completed</div>
                <div class="kpi-value" data-key="completed">–</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card overdue">
                <div class="kpi-label">Overdue</div>
                <div class="kpi-value" data-key="overdue">–</div>
            </div>
        </div>
    </div>
</div>
"""
            ).strip()
            script = script or (
                """
(function(){
    var $ = window.jQuery;
    var panel = root_element;
    var state = { mode: 'my', period: 'month', user: '', overdue_within_period: false, is_manager: false };

    function computeRange(period){
        var now = frappe.datetime.now_datetime();
        var start, end;
        if (period === 'today'){
            var d = frappe.datetime.get_today();
            start = d + ' 00:00:00'; end = d + ' 23:59:59';
        } else if (period === 'week'){
            // approx: last 7 days
            start = frappe.datetime.add_days(frappe.datetime.nowdate(), -6) + ' 00:00:00';
            end = frappe.datetime.now_datetime();
        } else if (period === 'month'){
            start = frappe.datetime.month_start() + ' 00:00:00';
            end = frappe.datetime.now_datetime();
        } else if (period === 'quarter'){
            // approx quarter start: 3 months ago month_start
            var md = frappe.datetime.add_months(frappe.datetime.nowdate(), -2);
            start = frappe.datetime.month_start(md) + ' 00:00:00';
            end = frappe.datetime.now_datetime();
        } else if (period === 'year'){
            var y = (new Date()).getFullYear() + '-01-01';
            start = y + ' 00:00:00'; end = frappe.datetime.now_datetime();
        }
        return {start:start, end:end};
    }

    function updateChartFromPanel(){
        var range = computeRange(state.period) || {};
        var filters = [];
        if (state.mode === 'my'){
            filters.push(["Visit","assigned_to","=",frappe.session.user]);
        } else if (state.user){
            filters.push(["Visit","assigned_to","=",state.user]);
        }
        if (range.start and range.end){
            filters.push(["Visit","scheduled_time",">=",range.start]);
            filters.push(["Visit","scheduled_time","<=",range.end]);
        }
        // map period to chart timespan/time_interval when possible
        var timespan = null, interval = null;
        if (state.period === 'week') { timespan = 'Last Week'; interval = 'Daily'; }
        else if (state.period === 'month') { timespan = 'Last Month'; interval = 'Daily'; }
        else if (state.period === 'quarter') { timespan = 'Last Quarter'; interval = 'Weekly'; }
        else if (state.period === 'year') { timespan = 'Last Year'; interval = 'Monthly'; }
        // save to user's dashboard settings so workspace reload/refresh uses it
        return frappe.xcall("frappe.desk.doctype.dashboard_settings.dashboard_settings.save_chart_config", {
            reset: 0,
            config: { filters: filters, timespan: timespan, time_interval: interval },
            chart_name: 'Visits Created'
        }).then(function(){
            // trigger that chart's refresh action if present, else reload workspace
            var $chart = $(document).find('.dashboard-widget-box .widget-head .widget-title').filter(function(){
                return $(this).text().trim() === 'Visits Created';
            }).closest('.dashboard-widget-box');
            var $refresh = $chart.find('.dropdown-menu a[data-action="action-refresh"]').first();
            if ($refresh.length){
                $refresh.trigger('click');
            } else if (frappe.workspace && frappe.workspace.reload) {
                frappe.workspace.reload();
            }
        });
    }

    function setMode(mode, showHint) {
        state.mode = mode;
        $(panel).find('.vm-mode-btn').removeClass('active');
        $(panel).find('.vm-mode-btn[data-mode="' + mode + '"]').addClass('active');
        $(panel).find('.vm-role-hint').toggleClass('d-none', !showHint);
        $(panel).find('.vm-agent').toggleClass('d-none', !(mode === 'team' && state.is_manager));
    }

    function setPeriod(period) {
        state.period = period;
        $(panel).find('.vm-period-select').val(period);
    }

    function setUser(user){
        state.user = user || '';
    }

    function renderValues(data){
        var keys = ['planned','in_progress','completed','overdue'];
        for (var i=0;i<keys.length;i++){
            var k = keys[i];
            // Avoid HTML-returning formatters; show plain, locale-safe numbers
            var val = data[k] || 0;
            $(panel).find('.kpi-value[data-key="' + k + '"]').text(String(val));
        }
        // role awareness
        state.is_manager = !!data.is_manager;
        if (data.effective_mode && data.effective_mode !== state.mode) {
            setMode(data.effective_mode, true);
        } else {
            $(panel).find('.vm-role-hint').toggleClass('d-none', !!state.is_manager);
        }
        $(panel).find('.vm-agent').toggleClass('d-none', !(state.mode === 'team' && state.is_manager));
    }

    function refresh(){
        return frappe.call({
            method: 'visit_management.utils.get_visit_kpis',
            args: { mode: state.mode, period: state.period, user: state.user, overdue_within_period: state.overdue_within_period },
        }).then(function(res){
            renderValues((res && res.message) || {});
            // also persist matching filters into user's chart settings and refresh chart
            try { updateChartFromPanel(); } catch (e) { /* no-op */ }
        });
    }

    function loadAgents(){
        return frappe.call({
            method: 'visit_management.utils.get_visit_assignees'
        }).then(function(res){
            var list = ((res && res.message) || []).filter(Boolean);
            var $sel = $(panel).find('.vm-agent-select');
            $sel.empty();
            $sel.append('<option value="">All</option>');
            list.forEach(function(u){ $sel.append('<option value="'+u+'">'+frappe.utils.escape_html(u)+'</option>'); });
        });
    }

    // events
    $(panel).find('.vm-mode-btn').on('click', function(){
        var mode = $(this).data('mode');
        setMode(mode, false);
        refresh();
    });
    $(panel).find('.vm-period-select').on('change', function(){
        var period = $(this).val();
        setPeriod(period);
        refresh();
    });
    $(panel).find('.vm-agent-select').on('change', function(){
        setUser($(this).val());
        refresh();
    });
    $(panel).find('.vm-overdue-scope').on('change', function(){
        state.overdue_within_period = $(this).is(':checked');
        refresh();
    });

    // init
    setMode('my', false);
    setPeriod('month');
    loadAgents().then(refresh);
})();
"""
            ).strip()
            style = style or (
                """
.vm-kpi-panel{padding:8px 0} .vm-kpi-toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px} .vm-kpi .kpi-card{background:#fff;border:1px solid var(--border-color, #d1d8dd);border-radius:6px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,0.03)} .kpi-label{font-size:12px;color:#6c757d;text-transform:uppercase;letter-spacing:.04em} .kpi-value{font-size:24px;font-weight:700;margin-top:4px} .kpi-card.planned{border-left:4px solid #6c757d} .kpi-card.in-progress{border-left:4px solid #17a2b8} .kpi-card.completed{border-left:4px solid #28a745} .kpi-card.overdue{border-left:4px solid #dc3545}
"""
            ).strip()

        # Upsert doc to ensure fields are present
        if frappe.db.exists("Custom HTML Block", chb_name):
            chb = frappe.get_doc("Custom HTML Block", chb_name)
            if html is not None:
                chb.html = html
            if script is not None:
                chb.script = script
            if style is not None:
                chb.style = style
            chb.flags.ignore_permissions = True
            chb.save()
        else:
            chb = frappe.get_doc({
                "doctype": "Custom HTML Block",
                "name": chb_name,
                "html": html or "<div class=\"text-muted\">Visits KPI Panel</div>",
                "script": script or "",
                "style": style or "",
            })
            chb.insert(ignore_permissions=True)
    except Exception:
        # non-fatal
        pass

    if not frappe.db.exists("Workspace", ws_name):
        ws = frappe.get_doc({
            "doctype": "Workspace",
            "name": ws_name,
            "label": ws_name,
            "title": ws_name,
            "module": "Visit Management",
            "public": 1,
            "is_standard": 1,
            "icon": "map-pin",
            "content": workspace_content,
            "shortcuts": workspace_shortcuts,
            "number_cards": workspace_cards,
            "charts": [{"chart_name": chart_name, "label": chart_name}],
            "custom_blocks": [{"custom_block_name": chb_name, "label": chb_name}],
        })
        ws.insert(ignore_permissions=True)
    else:
        # Avoid editing standard workspace on migrate; only update if non-standard
        try:
            ws = frappe.get_doc("Workspace", ws_name)
            if int(ws.get("is_standard") or 0) != 1:
                ws.update({
                    "label": ws_name,
                    "title": ws_name,
                    "module": "Visit Management",
                    "public": 1,
                    "icon": "map-pin",
                    "content": workspace_content,
                })
                # Update child tables
                ws.set("shortcuts", workspace_shortcuts)
                ws.set("number_cards", workspace_cards)
                ws.set("charts", [{"chart_name": chart_name, "label": chart_name}])
                ws.set("custom_blocks", [{"custom_block_name": chb_name, "label": chb_name}])
                ws.save(ignore_permissions=True)
        except Exception:
            pass

    frappe.clear_cache()
    # Upsert client custom fields and the frequency-overdue number card after workspace/chart setup
    try:
        _upsert_custom_fields_for_clients()
        _upsert_frequency_overdue_number_card()
    except Exception:
        pass
    return {
        "workspace": ws_name,
        "dashboard": dash_name,
        "chart": chart_name,
        "cards": [c["name"] for c in cards],
    }


def _upsert_frequency_overdue_number_card():
    """Create/Update a custom number card that shows overdue routine visits for clients.

    Also migrates from the previous name 'Visit Frequency Overdue'.
    """
    new_name = "Overdue Routine Visits"
    old_name = "Visit Frequency Overdue"
    # migrate/rename if old exists and new missing
    if frappe.db.exists("Number Card", old_name) and not frappe.db.exists("Number Card", new_name):
        try:
            frappe.rename_doc("Number Card", old_name, new_name, force=True)
        except Exception:
            pass

    name = new_name
    if frappe.db.exists("Number Card", name):
        try:
            doc = frappe.get_doc("Number Card", name)
            if int(doc.get("is_standard") or 0) != 1:
                doc.update({
                    "label": name,
                    "type": "Custom",
                    "method": "visit_management.utils.get_frequency_overdue_count",
                    "show_percentage_stats": 0,
                    "filters_json": "[]",
                    "dynamic_filters_json": "[]",
                    "currency": "",
                })
                doc.save(ignore_permissions=True)
        except Exception:
            pass
    else:
        frappe.get_doc({
            "doctype": "Number Card",
            "name": name,
            "label": name,
            "type": "Custom",
            "method": "visit_management.utils.get_frequency_overdue_count",
            "is_standard": 1,
            "is_public": 1,
            "show_percentage_stats": 0,
            "filters_json": "[]",
            "dynamic_filters_json": "[]",
            "currency": "",
        }).insert(ignore_permissions=True)


def _upsert_custom_fields_for_clients():
    """Create/ensure visit-frequency custom fields on client doctypes (Customer and CRM Organization)."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    fields = {
        # ERPNext Customer
        "Customer": [
            dict(fieldname="requires_regular_visits", label="Requires Regular Visits", fieldtype="Check", insert_after="customer_group"),
            dict(
                fieldname="visit_frequency",
                label="Visit Frequency",
                fieldtype="Select",
                options="\nWeekly\nBiweekly\nMonthly\nQuarterly\nSemiannual\nAnnual",
                depends_on="eval:doc.requires_regular_visits==1",
                insert_after="requires_regular_visits",
            ),
        ],
        # CRM Organization (from CRM app)
        "CRM Organization": [
            dict(fieldname="requires_regular_visits", label="Requires Regular Visits", fieldtype="Check", insert_after="organization_name"),
            dict(
                fieldname="visit_frequency",
                label="Visit Frequency",
                fieldtype="Select",
                options="\nWeekly\nBiweekly\nMonthly\nQuarterly\nSemiannual\nAnnual",
                depends_on="eval:doc.requires_regular_visits==1",
                insert_after="requires_regular_visits",
            ),
        ],
    }
    try:
        create_custom_fields(fields, ignore_validate=True)
    except Exception:
        pass


@whitelist()
def get_frequency_overdue_count():
    """Return count of clients (Customer + CRM Organization) that are overdue as per visit frequency."""
    import datetime

    def get_last_visit_for(client_doctype: str, client_name: str):
        # Prefer check_out_time, fallback to scheduled_time of Completed visit
        dt = frappe.db.sql(
            """
            select coalesce(max(check_out_time), max(scheduled_time))
            from `tabVisit`
            where status='Completed' and client_type=%s and client=%s
            """,
            (client_doctype, client_name),
        )
        return (dt[0][0] if dt and dt[0] and dt[0][0] else None)

    def due_date_from(last_dt, freq: str):
        if not last_dt:
            return None
        # normalize to date
        if isinstance(last_dt, str):
            try:
                last_dt = datetime.datetime.fromisoformat(last_dt)
            except Exception:
                last_dt = now_datetime()
        if freq == "Weekly":
            delta = datetime.timedelta(days=7)
        elif freq == "Biweekly":
            delta = datetime.timedelta(days=14)
        elif freq == "Monthly":
            # approximate as 30 days
            delta = datetime.timedelta(days=30)
        elif freq == "Quarterly":
            delta = datetime.timedelta(days=90)
        elif freq == "Semiannual":
            delta = datetime.timedelta(days=182)
        elif freq == "Annual":
            delta = datetime.timedelta(days=365)
        else:
            return None
        return (last_dt + delta).date()

    today = getdate()
    overdue = 0

    # Customers
    for row in frappe.get_all(
        "Customer",
        filters={"requires_regular_visits": 1},
        fields=["name", "visit_frequency"],
    ):
        last = get_last_visit_for("Customer", row.name)
        due = due_date_from(last, row.visit_frequency)
        if not due or due < today:
            overdue += 1

    # CRM Organizations
    if frappe.db.exists("DocType", "CRM Organization"):
        for row in frappe.get_all(
            "CRM Organization",
            filters={"requires_regular_visits": 1},
            fields=["name", "visit_frequency"],
        ):
            last = get_last_visit_for("CRM Organization", row.name)
            due = due_date_from(last, row.visit_frequency)
            if not due or due < today:
                overdue += 1

    return {"value": overdue, "fieldtype": "Int"}


@whitelist()
def get_visit_kpis(
    mode: str = "my",
    user: str | None = None,
    period: str = "month",
    from_date: str | None = None,
    to_date: str | None = None,
    overdue_within_period: int | bool | None = None,
):
    """Return visit KPI counts with role-aware scoping.

    Args:
        mode: "my" for current user, "team" for manager-wide view (requires Sales Manager/System Manager).
        user: optional specific user to scope to (only honored in team mode with permission).
        period: one of today|week|month|quarter|year|custom.
        from_date, to_date: when period==custom, ISO dates (YYYY-MM-DD).

    Returns: dict with counts: planned, in_progress, completed, overdue
    """
    current_user = frappe.session.user

    # Resolve team visibility (server-side: use frappe.get_roles)
    roles = set(frappe.get_roles(current_user))
    is_manager = ("Sales Manager" in roles) or ("System Manager" in roles)
    effective_mode = mode if (mode == "my" or is_manager) else "my"

    # Build base filter for user scope
    base_filters = []
    if effective_mode == "my":
        base_filters.append(["Visit", "assigned_to", "=", current_user])
    else:
        # team mode
        if user:
            base_filters.append(["Visit", "assigned_to", "=", user])
        # if no user specified and team mode, show all permitted users

    # Build period window for scheduled_time
    dt_now = now_datetime()
    start = end = None
    p = (period or "month").lower()
    if p == "today":
        d = getdate(dt_now)
        # use whole day boundaries
        start = f"{d} 00:00:00"
        end = f"{d} 23:59:59"
    elif p == "week":
        start_d = get_first_day_of_week(dt_now, as_str=True)
        end_d = get_last_day_of_week(dt_now)
        end = f"{end_d} 23:59:59"
        start = f"{start_d} 00:00:00"
    elif p == "month":
        start_d = get_first_day(dt_now)
        end_d = get_last_day(dt_now)
        start = f"{start_d} 00:00:00"
        end = f"{end_d} 23:59:59"
    elif p == "quarter":
        start_d = get_quarter_start(dt_now)
        end_d = get_quarter_ending(dt_now)
        start = f"{start_d} 00:00:00"
        end = f"{end_d} 23:59:59"
    elif p == "year":
        start_d = get_year_start(dt_now)
        end_d = get_year_ending(dt_now)
        start = f"{start_d} 00:00:00"
        end = f"{end_d} 23:59:59"
    elif p == "custom" and from_date and to_date:
        start = f"{from_date} 00:00:00"
        end = f"{to_date} 23:59:59"

    period_filters = []
    if start and end:
        period_filters.extend([
            ["Visit", "scheduled_time", ">=", start],
            ["Visit", "scheduled_time", "<=", end],
        ])

    def count_with(extra):
        return frappe.db.count("Visit", filters=(base_filters + period_filters + extra))

    planned = count_with([["Visit", "status", "=", "Planned"]])
    in_progress = count_with([["Visit", "status", "=", "In Progress"]])
    completed = count_with([["Visit", "status", "=", "Completed"]])

    # Overdue: not completed and scheduled_time < now (absolute overdue)
    overdue_filters_base = base_filters + [["Visit", "status", "in", ["Planned", "In Progress"]]]
    if overdue_within_period:
        # restrict within chosen period
        period_part = period_filters[:] if period_filters else []
        period_part.append(["Visit", "scheduled_time", "<", dt_now])
        overdue = frappe.db.count("Visit", filters=(overdue_filters_base + period_part))
    else:
        overdue = frappe.db.count(
            "Visit",
            filters=(
                overdue_filters_base
                + [["Visit", "scheduled_time", "<", dt_now]]
            ),
        )

    return {
        "planned": planned,
        "in_progress": in_progress,
        "completed": completed,
        "overdue": overdue,
        "effective_mode": effective_mode,
        "is_manager": bool(is_manager),
    }


@whitelist()
def get_visit_assignees():
    """Return distinct users assigned on Visit (enabled users only)."""
    # distinct assigned_to from Visit
    rows = frappe.db.get_all(
        "Visit",
        fields=["distinct assigned_to as user"],
        filters={"assigned_to": ["is", "set"]},
        as_list=False,
    )
    users = [r.get("user") for r in rows if r.get("user")]
    if not users:
        return []
    enabled = set(
        x.name
        for x in frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, fields=["name"])
    )
    return [u for u in users if u in enabled]


@whitelist()
def debug_workspace_payload(name: str = "Visits"):
    """Return minimal Workspace diagnostics: content types and custom block presence.

    Avoid returning Frappe objects to keep bench execute serialization simple.
    """
    page = frappe.get_doc("Workspace", name)
    import json
    content = page.content or "[]"
    decoded = None
    try:
        decoded = json.loads(content)
    except Exception as e:
        decoded = {"error": str(e), "raw": content}
    content_types = []
    has_cb = False
    if isinstance(decoded, list):
        content_types = [x.get("type") for x in decoded if isinstance(x, dict)]
        has_cb = any((x.get("type") == "custom_block") for x in decoded if isinstance(x, dict))
    cb_child = [row.custom_block_name for row in (page.custom_blocks or [])]
    return {
        "content_block_types": content_types,
        "has_custom_block_in_content": has_cb,
        "custom_blocks_child": cb_child,
    }


@whitelist()
def debug_custom_block_info(name: str = "Visits KPI Panel"):
    """Return basic details of a Custom HTML Block to verify import and content presence."""
    if not frappe.db.exists("Custom HTML Block", name):
        return {"exists": False}
    doc = frappe.get_doc("Custom HTML Block", name)
    return {
        "exists": True,
        "private": bool(doc.get("private")),
        "html_len": len(doc.get("html") or ""),
        "script_len": len(doc.get("script") or ""),
        "style_len": len(doc.get("style") or ""),
        "roles": [r.role for r in (doc.get("roles") or [])],
    }


@whitelist()
def upsert_visits_kpi_panel_block():
        """Force-update the 'Visits KPI Panel' Custom HTML Block with embedded HTML/JS/CSS."""
        name = "Visits KPI Panel"
        html = (
                """
<div class="vm-kpi-panel">
    <div class="vm-kpi-toolbar">
        <div class="left d-flex align-items-center">
            <div class="btn-group btn-group-sm mr-2">
                <button type="button" class="btn btn-default vm-mode-btn active" data-mode="my">My</button>
                <button type="button" class="btn btn-default vm-mode-btn" data-mode="team">Team</button>
            </div>
            <div class="vm-agent d-none">
                <label class="mr-2 text-muted">Agent</label>
                <select class="form-control input-sm vm-agent-select"><option value="">All</option></select>
            </div>
        </div>
        <div class="right d-flex align-items-center">
            <div class="vm-period mr-2">
                <label class="mr-2 text-muted">Period</label>
                <select class="form-control input-sm vm-period-select">
                    <option value="today">Today</option>
                    <option value="week">This Week</option>
                    <option value="month" selected> This Month</option>
                    <option value="quarter">This Quarter</option>
                    <option value="year">This Year</option>
                </select>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input vm-overdue-scope" type="checkbox" id="vmOverdueScope">
                <label class="form-check-label" for="vmOverdueScope">Overdue within period</label>
            </div>
            <span class="vm-role-hint badge badge-warning ml-2 d-none">Limited to My</span>
        </div>
    </div>
    <div class="vm-kpis row">
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card planned">
                <div class="kpi-label">Planned</div>
                <div class="kpi-value" data-key="planned">–</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card in-progress">
                <div class="kpi-label">In Progress</div>
                <div class="kpi-value" data-key="in_progress">–</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card completed">
                <div class="kpi-label">Completed</div>
                <div class="kpi-value" data-key="completed">–</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 vm-kpi">
            <div class="kpi-card overdue">
                <div class="kpi-label">Overdue</div>
                <div class="kpi-value" data-key="overdue">–</div>
            </div>
        </div>
    </div>
</div>
"""
        ).strip()
        script = (
                """
(function(){
    var $ = window.jQuery;
    var panel = root_element;
    var state = { mode: 'my', period: 'month', user: '', overdue_within_period: false, is_manager: false };

    function setMode(mode, showHint) {
        state.mode = mode;
        $(panel).find('.vm-mode-btn').removeClass('active');
        $(panel).find('.vm-mode-btn[data-mode="' + mode + '"]').addClass('active');
        $(panel).find('.vm-role-hint').toggleClass('d-none', !showHint);
        $(panel).find('.vm-agent').toggleClass('d-none', !(mode === 'team' && state.is_manager));
    }

    function setPeriod(period) {
        state.period = period;
        $(panel).find('.vm-period-select').val(period);
    }

    function setUser(user){
        state.user = user || '';
    }

    function renderValues(data){
        var keys = ['planned','in_progress','completed','overdue'];
        for (var i=0;i<keys.length;i++){
            var k = keys[i];
            // Avoid HTML-returning formatters; show plain, locale-safe numbers
            var val = data[k] || 0;
            $(panel).find('.kpi-value[data-key="' + k + '"]').text(String(val));
        }
        // role awareness
        state.is_manager = !!data.is_manager;
        if (data.effective_mode && data.effective_mode !== state.mode) {
            setMode(data.effective_mode, true);
        } else {
            $(panel).find('.vm-role-hint').toggleClass('d-none', !!state.is_manager);
        }
        $(panel).find('.vm-agent').toggleClass('d-none', !(state.mode === 'team' && state.is_manager));
    }

    function refresh(){
        return frappe.call({
            method: 'visit_management.utils.get_visit_kpis',
            args: { mode: state.mode, period: state.period, user: state.user, overdue_within_period: state.overdue_within_period },
        }).then(function(res){
            renderValues((res && res.message) || {});
        });
    }

    function loadAgents(){
        return frappe.call({
            method: 'visit_management.utils.get_visit_assignees'
        }).then(function(res){
            var list = ((res && res.message) || []).filter(Boolean);
            var $sel = $(panel).find('.vm-agent-select');
            $sel.empty();
            $sel.append('<option value="">All</option>');
            list.forEach(function(u){ $sel.append('<option value="'+u+'">'+frappe.utils.escape_html(u)+'</option>'); });
        });
    }

    // events
    $(panel).find('.vm-mode-btn').on('click', function(){
        var mode = $(this).data('mode');
        setMode(mode, false);
        refresh();
    });
    $(panel).find('.vm-period-select').on('change', function(){
        var period = $(this).val();
        setPeriod(period);
        refresh();
    });
    $(panel).find('.vm-agent-select').on('change', function(){
        setUser($(this).val());
        refresh();
    });
    $(panel).find('.vm-overdue-scope').on('change', function(){
        state.overdue_within_period = $(this).is(':checked');
        refresh();
    });

    // init
    setMode('my', false);
    setPeriod('month');
    loadAgents().then(refresh);
})();
"""
        ).strip()
        style = (
                """
.vm-kpi-panel{padding:8px 0} .vm-kpi-toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px} .vm-kpi .kpi-card{background:#fff;border:1px solid var(--border-color, #d1d8dd);border-radius:6px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,0.03)} .kpi-label{font-size:12px;color:#6c757d;text-transform:uppercase;letter-spacing:.04em} .kpi-value{font-size:24px;font-weight:700;margin-top:4px} .kpi-card.planned{border-left:4px solid #6c757d} .kpi-card.in-progress{border-left:4px solid #17a2b8} .kpi-card.completed{border-left:4px solid #28a745} .kpi-card.overdue{border-left:4px solid #dc3545}
"""
        ).strip()

        if frappe.db.exists("Custom HTML Block", name):
                doc = frappe.get_doc("Custom HTML Block", name)
                doc.update({"html": html, "script": script, "style": style})
                doc.save(ignore_permissions=True)
        else:
                doc = frappe.get_doc({
                        "doctype": "Custom HTML Block",
                        "name": name,
                        "html": html,
                        "script": script,
                        "style": style,
                })
                doc.insert(ignore_permissions=True)
        frappe.clear_cache(doctype="Custom HTML Block")
        return {"ok": True}
