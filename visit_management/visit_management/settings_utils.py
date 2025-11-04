from __future__ import annotations

import frappe


def get_settings() -> dict:
    """Return Visit Management Settings as a dict; safe defaults if missing."""
    defaults = {
        "enable_hr_integration": True,
        "require_photo_for_checkin": True,
        "require_photo_for_checkout": True,
        "require_geolocation": False,
        "default_visit_duration": 60,
        "auto_create_visits_from_schedule": True,
        "enable_visit_notifications": True,
        "enable_image_compression": True,
        "image_max_dimension": 1280,
        "image_quality": 80,
    }
    try:
        if frappe.db.exists("DocType", "Visit Management Settings"):
            doc = frappe.get_cached_doc("Visit Management Settings")
            for k in list(defaults.keys()):
                defaults[k] = getattr(doc, k, defaults[k])
    except Exception:
        pass
    return defaults


def is_photo_required(checkout: bool = False) -> bool:
    s = get_settings()
    return bool(s.get("require_photo_for_checkout" if checkout else "require_photo_for_checkin", True))


def require_geolocation_on_completion() -> bool:
    s = get_settings()
    return bool(s.get("require_geolocation", False))


def get_roles_exempt_from_checkin() -> set[str]:
    """Return set of role names that are exempt from mandatory check-in."""
    try:
        if frappe.db.exists("DocType", "Visit Management Settings"):
            doc = frappe.get_cached_doc("Visit Management Settings")
            rows = getattr(doc, "allowed_checkin_roles", []) or []
            return set([getattr(r, "role", None) for r in rows if getattr(r, "role", None)])
    except Exception:
        pass
    return set()


def is_checkin_mandatory_for_user(user: str | None = None) -> bool:
    """Return True if the user must Check-in before completing a visit.

    Users having any role listed under settings.allowed_checkin_roles are EXEMPT
    from mandatory check-in; for all others, check-in is mandatory.
    """
    try:
        user = user or frappe.session.user
        exempt = get_roles_exempt_from_checkin()
        if not exempt:
            return True  # no exemptions configured
        roles = set(frappe.get_roles(user))
        return roles.isdisjoint(exempt)
    except Exception:
        # on any error, default to mandatory for safety
        return True
