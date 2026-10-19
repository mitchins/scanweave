#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/../.."
export SCANWEAVE_M1D_EVIDENCE="$PWD/qualification/pdf_packaging/rust-m1d"
cargo test --workspace -- --skip regress_auto_reports_the_selected_candidate --skip clearscan_repairs_a_damaged_glyph_from_same_document_donors
# Both inherited failures are rerun independently and retained, not erased.
cargo test -p m0-font-pdf --test m1b_behavior regress_auto_reports_the_selected_candidate
cargo test -p m0-font-pdf --test m1d_reconstruction clearscan_repairs_a_damaged_glyph_from_same_document_donors
"${PYTHON:-python3}" qualification/checks.py --out qualification/pdf_packaging/e0-e7-p01-p08.json
