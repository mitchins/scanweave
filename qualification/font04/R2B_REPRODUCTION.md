# R2b P2 stop receipt

P2 was opened once at `0809db3` using the retained R2a binary. See
`r2b-stop-receipt.json` for the lock, precheck facts, complete per-sheet run
receipts, timings, RSS and functional checks. `local/P2-preflight` is an
abandoned partial financial preflight and was not used. P2 inputs and outputs
remain under `local/P2`; the lock must be retained.

All nine pages were split from the generated scan PDF and converted serially
with four Rayon threads and one OpenMP thread at each sheet's native DPI.
Run `PYTHONPATH=qualification/font04/local/R2a/pdfium-python:. qualification/.venv/bin/python -m qualification.font04.r2b_run`
only to resume verified existing outputs, never to regenerate P2. The actual
run used the equivalent temporary script recorded in the receipts.

A full-page-context diagnostic compares each observation box to a composite
of all pristine glyphs at their original coordinates. The command is
`PYTHONPATH=qualification/font04/local/R2a/pdfium-python:. qualification/.venv/bin/python -m qualification.font04.r2b_pristine`.
It includes all 6,768 observations per renderer, but overlapping neighbours are
also counted. Its class screen fails in both renderers. This is not established
as the frozen isolated-glyph quality metric; the result requires independent
interpretation and must not be represented as a definitive isolated-glyph
qualification. The harness dimension correction and hash evidence are in
`r2b-harness-fixes.json`.

Stopped at the adverse pristine screen under the brief's stop rule. Full
isolated-glyph quality, false rejection, outline accounting, and the sealed
blind package are not completed. Material defects are pending review; no
product or method change was made.
