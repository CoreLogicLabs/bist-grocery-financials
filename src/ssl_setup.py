"""SSL setup for environments behind a TLS-intercepting AV/proxy (e.g. Norton).

Two HTTP stacks are in play:
  * borsapy / requests  -> Python's ``ssl`` module  -> fixed by ``truststore``.
  * yfinance / curl_cffi -> libcurl                  -> ignores Python ssl;
    must be pointed at a CA bundle via ``CURL_CA_BUNDLE`` / ``SSL_CERT_FILE``.

We build one combined PEM = certifi roots + the Windows trust store (which
contains the local interception root), then export it through the env vars
libcurl honours. Certificate verification is never disabled.
"""
from __future__ import annotations
import os
import ssl
from pathlib import Path

import certifi

from .config import CACHE

_COMBINED_PEM = CACHE / "combined_ca.pem"
_WINDOWS_STORES = ("ROOT", "CA")


def _windows_roots_pem() -> str:
    """Return all Windows trust-store certs as concatenated PEM text."""
    if not hasattr(ssl, "enum_certificates"):  # non-Windows: nothing to add
        return ""
    chunks: list[str] = []
    seen: set[bytes] = set()
    for store in _WINDOWS_STORES:
        try:
            for der, _enc, _trust in ssl.enum_certificates(store):
                if der in seen:
                    continue
                seen.add(der)
                chunks.append(ssl.DER_cert_to_PEM_cert(der))
        except (OSError, ValueError):
            continue
    return "\n".join(chunks)


def build_ca_bundle(force: bool = False) -> Path:
    """Write (and cache) the combined certifi + OS CA bundle; return its path."""
    if _COMBINED_PEM.exists() and not force:
        return _COMBINED_PEM
    parts = [Path(certifi.where()).read_text(encoding="utf-8", errors="ignore"),
             _windows_roots_pem()]
    _COMBINED_PEM.write_text("\n".join(parts), encoding="utf-8")
    return _COMBINED_PEM


def configure_ssl(verbose: bool = False) -> Path:
    """Idempotently configure SSL for both HTTP stacks. Call once at startup."""
    # 1) Python ssl stack (borsapy / requests) via OS trust store.
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:  # truststore optional; curl path below still works
        pass

    # 2) libcurl stack (yfinance / curl_cffi) via combined CA bundle.
    bundle = build_ca_bundle()
    for var in ("CURL_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        os.environ.setdefault(var, str(bundle))

    if verbose:
        print(f"[ssl_setup] combined CA bundle -> {bundle}")
    return bundle


if __name__ == "__main__":
    configure_ssl(verbose=True)
