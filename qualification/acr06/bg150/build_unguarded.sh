#!/bin/bash
# Research-only 150-DPI assembly with metrics; layout still uses main's 200 DPI.
set -euo pipefail
repo=/tmp/scanweave-bg150
out=/tmp/bg150-ung-reproduce
mkdir -p "$out"
git -C "$repo" archive 36ad4eaf4eee8084335ea5f4be3ecc2a4ab6fc2e | tar -xf - -C "$out"
patch -d "$out" -p1 < /data/coding/scanweave/qualification/acr06/bg150/unguarded.patch
CARGO_TARGET_DIR=/tmp/bg150-ung-reproduce-target cargo build --release --locked --manifest-path "$out/Cargo.toml"
