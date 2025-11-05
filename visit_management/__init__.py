__version__ = "0.1.0"

# Bridge: ensure imports of visit_management.visit_management.doctype resolve to the deep package
import sys as _sys
from importlib import import_module as _import_module

try:
	# Import deep package: visit_management.visit_management.doctype
	_deep_path = __name__ + '.visit_management.doctype'
	_deep_doctype = _import_module(_deep_path)
	# Optional alias for visit_management.doctype if any code uses it
	_sys.modules[__name__ + '.doctype'] = _deep_doctype
	# Ensure the fully qualified key exists (usually populated by import already)
	_sys.modules[_deep_path] = _deep_doctype
except Exception:
	# Be permissive during partial installs/migrations
	pass
