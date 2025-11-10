import json
import frappe
import ast


def execute():
    """Normalize Visit.location to a JSON string with {"lat": float, "lng": float} or set NULL.

    Handles various legacy/bad forms:
    - Python dict literal strings: "{'lat': 7.1, 'lng': 3.5}" -> JSON
    - Non-JSON strings like "lat=7.1,lng=3.5" -> parse and JSON
    - Empty/invalid values -> set to NULL
    If the value is already a JSON string with lat/lng, it's preserved (pruned to these keys).
    """
    if not frappe.db.exists("DocType", "Visit"):
        return

    meta = frappe.get_meta("Visit")
    if not meta.has_field("location"):
        return

    rows = frappe.get_all(
        "Visit",
        filters={"location": ["is", "set"]},
        fields=["name", "location"],
        limit=100000,
    )

    updated = 0

    def to_json_payload(val):
        # Return a dict with lat/lng or None
        if val is None:
            return None
        # If it's already a dict
        if isinstance(val, dict):
            out = {}
            if "lat" in val:
                try:
                    out["lat"] = float(val["lat"]) if val["lat"] is not None else None
                except Exception:
                    pass
            if "lng" in val:
                try:
                    out["lng"] = float(val["lng"]) if val["lng"] is not None else None
                except Exception:
                    pass
            return out or None
        # Must be a string beyond this
        if not isinstance(val, str):
            return None
        s = (val or "").strip()
        if not s:
            return None
        # Try JSON first
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                return to_json_payload(obj)
            except Exception:
                pass
        # Try python literal dict
        try:
            obj = ast.literal_eval(s)
            return to_json_payload(obj)
        except Exception:
            pass
        # Try simple "lat=..,lng=.." form
        try:
            parts = dict(
                (k.strip(), v.strip())
                for k, v in (seg.split("=", 1) for seg in s.split(",") if "=" in seg)
            )
            lat = float(parts.get("lat")) if parts.get("lat") not in (None, "") else None
            lng = float(parts.get("lng")) if parts.get("lng") not in (None, "") else None
            if lat is not None or lng is not None:
                return {"lat": lat, "lng": lng}
        except Exception:
            pass
        return None

    for row in rows:
        name = row.get("name")
        val = row.get("location")
        try:
            payload = to_json_payload(val)
            if payload is None:
                # Clear invalid/empty values
                frappe.db.set_value("Visit", name, "location", None, update_modified=False)
                updated += 1
                continue
            # Re-serialize with only lat/lng
            serialized = frappe.as_json({k: payload[k] for k in ("lat", "lng") if k in payload})
            if serialized != val:
                frappe.db.set_value("Visit", name, "location", serialized, update_modified=False)
                updated += 1
        except Exception:
            # On any unexpected error for a row, skip but proceed
            continue

    frappe.db.commit()
    frappe.clear_cache(doctype="Visit")
    frappe.logger().info(f"Geolocation normalization patch updated {updated} Visit rows")
