# Experimental reduced backgrounds

`--experimental-background-dpi 150` opts PDF input into an experimental
ClearScan background representation. The only accepted value is `150`; without
the option the existing output is used. The encoder considers only eligible
whole-page backgrounds that the existing encoder already reduces, and retains
the existing representation unless the smaller JPEG passes a conservative
source-pixel round-trip test. The log records per-page decisions and metrics.

The experiment leaves layout cost calculations unchanged. It is disabled in
auto mode and when glyph sharing is enabled, because their complete-PDF size
comparisons could otherwise change which representation or font is selected.
Faithful and protected documents retain their existing paths. This option is
for measurement and independent review, not a new default or a fidelity claim.
