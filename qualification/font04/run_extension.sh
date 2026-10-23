#!/bin/sh
set -eu
export PYTHONPATH=.
export FONT04_CAUSAL_ROOT=qualification/font04/local/causal-extension
export FONT04_CAUSAL_CLASSES=odynstru
for split in train validation test; do
 qualification/.venv/bin/python qualification/font04/causal.py prepare "$split"
 qualification/.venv/bin/python qualification/font04/causal.py atlas "$split"
 qualification/.venv/bin/python qualification/font04/causal.py evaluate "$split"
done
