#!/usr/bin/env python3
"""External-tool resolution for the qualification harness.

The harness sits on top of two locally built tools (qpdf, the OTS sanitizer)
that live under `tools/` in a developer checkout but are NOT committed (the
directory is git-ignored). In any other environment — a clean checkout, CI, a
contributor's machine — they come from the system instead.

Resolution order for each tool:

1. an explicit environment override (`SCANWEAVE_QPDF`, `SCANWEAVE_OTS`),
2. the locally built binary under `tools/`,
3. the tool on `PATH` (e.g. the distro package).

A missing tool is reported as a hard error at the call site, never silently
skipped: a gate that cannot check is a failing gate, not a passing one.
"""
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _first_existing(candidates: list[str]) -> str | None:
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def _on_path(name: str) -> str | None:
    return shutil.which(name)


def qpdf_bin() -> str:
    """The qpdf executable (structural PDF checks and QDF dumps)."""
    override = os.environ.get("SCANWEAVE_QPDF")
    if override:
        return override
    local = _first_existing([os.path.join(ROOT, "tools", "dist", "bin", "qpdf")])
    if local:
        return local
    system = _on_path("qpdf")
    if system:
        return system
    raise RuntimeError(
        "qpdf not found: set SCANWEAVE_QPDF, build tools/dist, or install qpdf "
        "(apt-get install qpdf)"
    )


def qpdf_env() -> dict:
    """Environment for qpdf: the local build's shared libraries when present."""
    env = dict(os.environ)
    local_lib = os.path.join(ROOT, "tools", "dist", "lib")
    if os.path.isdir(local_lib):
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = (
            local_lib + (":" + existing if existing else "")
        )
    return env


def ots_bin() -> str:
    """The OpenType sanitizer (font program validity)."""
    override = os.environ.get("SCANWEAVE_OTS")
    if override:
        return override
    local = _first_existing(
        [os.path.join(ROOT, "tools", "src", "ots-bin", "ots-9.3.0-Linux", "ots-sanitize")]
    )
    if local:
        return local
    system = _on_path("ots-sanitize")
    if system:
        return system
    raise RuntimeError(
        "ots-sanitize not found: set SCANWEAVE_OTS or build tools/src/ots-bin"
    )


def version(binary: str) -> str:
    try:
        r = subprocess.run([binary, "--version"], capture_output=True, text=True)
    except OSError as e:  # pragma: no cover - environment failure
        return f"unavailable: {e}"
    return (r.stdout or r.stderr).splitlines()[0] if (r.stdout or r.stderr) else "unknown"
