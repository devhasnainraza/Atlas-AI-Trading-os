"""The auth module's only legal import surface (docs/module-conventions.md).

Grows with the phases: ``build_auth_module`` now, the authorization dependencies
(``Principal``, ``current_principal``, ``require_permissions``) with the middleware and RBAC
work. Anything not re-exported here is private to the module — ``lint-imports`` enforces it.
"""

from atlas_api.modules.auth.router import build_auth_module

__all__ = ["build_auth_module"]
