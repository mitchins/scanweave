# Toolchain and validator inventory (WP-A)

Recorded: 2026-10-13. Environment: Ubuntu 24.04.x, Linux 7.0.0-31-generic, x86_64, 24 CPUs,
78 GiB RAM. This file is the M0 "doctor" baseline. Every consumer of these tools must
distinguish an unavailable validator (`NOT_RUN`) from a passing check.

## Build toolchain

| Tool | Version | Source | Notes |
|---|---|---|---|
| rustc | 1.99.0 (b940084d7 2026-09-28) | rustup, installed this session | pinned via `rust-toolchain.toml` (channel `1.99.0`) |
| cargo | 1.99.0 (5f9046... 2026-08-27) | rustup | `Cargo.lock` committed; `--locked` builds |
| gcc/g++/clang/cmake/make | system | Ubuntu 24.04 | used for local validator builds only |

## Runtime crates

Pinned in `UPSTREAMS.lock.toml` (WP-B). Registry access verified: sparse index + static
downloads HTTP 200. No network is used at document-processing time.

## Validation tools

| Tool | Version | Provenance | Status | Path |
|---|---|---|---|---|
| Poppler pdftotext/pdftoppm/pdfinfo | 24.02.0 | system apt | AVAILABLE | /usr/bin |
| fontTools | 4.46.0 | system python3 | AVAILABLE | system site-packages |
| qpdf | 12.4.2 | built from source tarball `qpdf-12.4.2.tar.gz` sha256 `8a58af5b6141319287c1883bec8bd1bd545b7567b7fc5e6ce5d25a1c85f36397` (github release) | AVAILABLE | `tools/dist/bin/qpdf` (needs `LD_LIBRARY_PATH=tools/dist/lib`) |
| ots-sanitize | 9.3.0 | upstream prebuilt Linux release zip sha256 `1caab4037806688203efd124b97443694794ca69a3dddd9a42b4833a4f8c4967` (source tar.xz sha256 `23814f8e90ee77379f54e86a012c09bba2d133940e5257546b29cf087a73beec`) | AVAILABLE | `tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize` |
| PDFium | chromium/8100 (bblanchon/pdfium-binaries latest at setup) | release `pdfium-linux-x64.tgz` sha256 `1c1894a12d4d96ee01400c3874444126254180c5c7d2ab628576b67f8120320a` | AVAILABLE (shared lib; used via bindings from qualification harness) | `tools/src/pdfium/lib/libpdfium.so` |
| tesseract | — | apt candidate 5.3.4 exists but session has no root (`sudo` requires password); source build deferred | **UNAVAILABLE** | — |

Validator policy consequences:

- Structural checks: `qpdf --check` AVAILABLE.
- Independent font parsing/OTS: fontTools + ots-sanitize AVAILABLE.
- Independent render/extraction engine #1: Poppler AVAILABLE.
- Independent render/extraction engine #2: PDFium via bindings (REQUIRED route per approved
  plan; PyMuPDF fallback if binding fails — licence note would then apply).
- OCR subprocess: tesseract UNAVAILABLE. M0 synthetic probes supply OCR as input; no probe
  requires OCR invocation. Convenience-OCR routes are untestable in this environment and are
  recorded as such, not as passes.

## Fixture fonts (qualification harness only; never committed)

System-installed: DejaVu (Sans/Serif/Mono + Bold), Liberation family, Noto Sans Mono,
fonts-japanese-gothic.ttf, IPA Gothic (ipafont-gothic), WQY. Used only to rasterize synthetic
scans; reconstruction never reads these files.
