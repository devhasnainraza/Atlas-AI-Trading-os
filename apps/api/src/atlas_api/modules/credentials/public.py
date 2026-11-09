"""The credential vault's only legal import surface (docs/module-conventions.md).

``use_credential`` — the sole path from stored ciphertext to usable plaintext, and the port
Spec 03's trading adapters already depend on — is added here in T049. It is deliberately the
same file as the module builder: one import surface, one thing to audit.
"""

from atlas_api.modules.credentials.router import build_credentials_module

__all__ = ["build_credentials_module"]
