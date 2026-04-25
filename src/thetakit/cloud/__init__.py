"""Optional cloud-eval integration for thetakit.

Requires the `thetakit-cloud-client` package to be installed. CLI commands
(`thetakit auth`, `smoke-eval`, `full-eval`, etc.) soft-import this module
and print a helpful error if the client isn't available.
"""

from __future__ import annotations


def _require_client():
    try:
        from thetakit_cloud_client import CloudClient, load_credentials, save_credentials  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "The 'thetakit-cloud-client' package is not installed. "
            "Install it via the hosted-service setup in thetakit-cloud/README.md."
        ) from e
