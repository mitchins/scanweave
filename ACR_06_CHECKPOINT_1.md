# ACR-06 Checkpoint 1: comparator readiness

The starting point is `main` at `79b30e54907baedc76d0649ad17a7b2ebc749fda`, with FONT-04 q3 merged as opt-in. This is a new phase. All FONT-04 and earlier ACR evidence is unchanged.

## A1: Reconciled Adobe XI evidence

**Already established, so it will not be repeated:**

- **Frozen Acrobat XI Pro 11.0.20 ClearScan outputs** exist, with hashes, for the full 32-page development corpus. They were made under Wine 9.0 / Xvfb via `adobe-acrobat-sandbox/clearscan.sh`, with ClearScan and "Downsample To 600dpi"; the actual backgrounds are about 150 DPI. Outputs:
  - financial 718,276 B (`0168c79a…`)
  - historical 1,682,427 B (`0b5768a0…`)
  - receipts 915,781 B (`74ee49ed…`)
  - mixed 235,999 B (`c1f37db2…`)
  - forms 625,620 B (`b5b6ced3…`)
  - total 4,178,103 B
  - Earlier synthetic outputs: 8-page set 37,100 / 50,779 B at 300/600 DPI; 3-page set 46,213 / 51,429 B. Each has an exact-size glyph IoU recorded.
- **Prior Adobe findings:** Adobe reconstructs real text as embedded `CIDFontType0C` (CFF). Its backgrounds are much smaller and lower resolution. Its fidelity on synthetic text is at parity with ScanWeave, not better. The earlier `08431a7` measurement put PDFium glyph IoU at 0.903 / 0.942 for Adobe against 0.911 / 0.943 for ScanWeave.
- **Experiments already rejected, which will not be reintroduced:**
  - opaque native-crop / reduced-paper layering (ACR-05 root cause: paper resampled twice);
  - decontaminated foreground with 8-bit SMask (ACR-05 candidate B, 17.7 MB financial, new rectangular surrounds);
  - blanket native guards around every vector glyph;
  - broad residual tiles and connected residuals;
  - grayscale contour variants;
  - the ACR-02 composition.
- **Codec work already done:** the ACR-04/05 settings are in production. Whole-page residuals use about 200 DPI JPEG Q85 4:2:0, native exceptions use Q90 4:4:4, and pages with heavy fragmentation fall back to one coherent residual.

**New at this checkpoint:** one consistent stream inventory of Adobe XI against current `main` default ClearScan, produced by `qualification/acr06/quick_inventory.py` (`checkpoint1-inventory.json`). The `main` outputs are the FONT-04 baseline PDFs, which were confirmed byte-identical to a `main` build during the PR #26 parity check.

| Group | Adobe B | ScanWeave B | Gap | Raster A / S | Fonts A / S | Other streams A / S | Structure A / S |
|---|---:|---:|---:|---:|---:|---:|---:|
| financial (13 pp) | 718,276 | 2,849,237 | 3.97× | 274,998 / 1,973,037 | 297,667 / 727,259 | 118,542 / 144,916 | 27,069 / 4,025 |
| historical (5) | 1,682,427 | 2,266,058 | 1.35× | 1,116,016 / 2,198,254 | 482,803 / 3,472 | 70,000 / 62,471 | 13,608 / 1,861 |
| receipts (10) | 915,781 | 1,271,232 | 1.39× | 751,643 / 1,225,629 | 112,472 / 16,712 | 38,749 / 20,587 | 12,917 / 8,304 |
| mixed (2) | 235,999 | 917,603 | 3.89× | 89,724 / 506,626 | 107,583 / 249,013 | 31,441 / 76,116 | 7,251 / 85,848 |
| forms (2) | 625,620 | 843,699 | 1.35× | 290,066 / 736,983 | 270,922 / 41,147 | 54,351 / 64,508 | 10,281 / 1,061 |
| **total** | **4,178,103** | **8,147,829** | **1.95×** | | | | |

**What Adobe XI's output contains:**

- **Images:** only JPEG. Every image is RGB `DCTDecode`, sometimes wrapped in Flate. There are no JBIG2, CCITT, JPEG2000, SMask or ImageMask resources anywhere in the corpus.
- **Fonts:** CFF CID fonts throughout.
- **Financial pages:** about 10 full-page backgrounds at 907×1328 px (about 150 DPI on the 435 pt page), plus many 16 px JPEG tiles.

So Adobe's smaller files don't come from an exotic codec. They come from:

1. lower background resolution;
2. replacing more text with glyphs;
3. a CFF font representation.

**Two findings that change the framing:**

- **Adobe turns far more text into glyphs than ScanWeave does.** On historical pages it embeds 483 KB of fonts against ScanWeave's 3.5 KB, and on forms 271 KB against 41 KB. Some of Adobe's raster saving therefore comes from converting text that ScanWeave keeps as image. Whether those Fraktur and form glyphs are correct is still unverified, and on historical typography it could be content damage.
- **Forms are one case where ScanWeave is not using JPEG.** The default keeps forms as 737 KB of lossless Flate, while Adobe uses about 290 KB of JPEG. Financial remains the largest absolute gap: about 1.70 MB of extra raster and 0.43 MB of extra font.

**Still uncertain, and worth new experiments:**

1. What Adobe's 150 DPI backgrounds keep or drop on real pages: faint rules, punctuation, stains, artwork and unsupported ink. This needs a source-referenced content accounting, not byte comparisons.
2. Where Adobe's font bytes go: glyph count × bytes per glyph × CFF-versus-TrueType overhead. The financial fonts are 298 KB against ScanWeave's 727 KB.
3. Whether Adobe's extra vector text is correct. This needs reading-size and zoomed visual classification, plus extraction and search.
4. Visual classification at reading size of the five difference classes the mission defines, done for Adobe on real pages. This was previously done only on synthetic text and selected financial views.

## A2: CamScanner status

The provenance record is `qualification/acr06/camscanner-provenance.json`.

- **Official installer:** obtained from camscanner.com. The page's script resolves the Windows x64 link to `cs-dl.camscanner.com/download/CamScanner-1.90.0-online11051943-x64-Setup.exe`: 229,736,184 B, SHA-256 `ddb5cc0a…c8c46a`.
- **Signature:** the Authenticode chain is 上海临冠数据科技有限公司 (Shanghai Linguan Data Technology), issued by DigiCert Trusted G4 Code Signing CA1. The digest itself has not yet been verified inside Windows.
- **What it is:** a Squirrel installer for an Electron app, "CamScanner Desktop App" 1.90.0. It bundles a native `@ccint/pageScan` module, whose strings show OpenCV and the MNN inference engine, its own PDFium, libvips, and adb for phone linking. That's consistent with local enhancement, but this is not yet established.
- **Wine 9.0, in an isolated prefix (`~/.wine-camscanner-acr06`, Xvfb :161):** fails.
  - The installer hangs, because there is no wine-mono for Squirrel's .NET `Update.exe`.
  - Launching the payload directly aborts on `Unimplemented function ole32.dll.CoCancelCall`.
- **Windows VM fallback:** prepared but **blocked**. It's an overlay on the FONT-04 Windows 11 evaluation disk, which is made read-only and never written, with separate firmware variables and TPM state, its own share, and VNC :18. QEMU fails with `Could not access KVM kernel module: Permission denied`, because this session no longer has `/dev/kvm` access. This needs owner action.
- **Planned once the VM boots:**
  - Verify the signature.
  - Install with the official installer.
  - First run with the network disabled (`-nic user,restrict=on`) to establish whether import, enhancement and export work locally and without an account.
  - Record every UI mode name and any forced resampling.
  - Use the network only if it's required, and then only with public-domain or appropriately licensed inputs.
  - If it turns out to be a cloud viewer or needs a phone, report that and continue with the Adobe/ScanWeave work.

## A3: Chosen matched inputs

Every input is an existing frozen source with an existing Adobe XI output, so Adobe needs no rerun.

| Role | Source (frozen) | Why |
|---|---|---|
| Financial numerals | financial `annual-021` | dense fine numerals; inspected in ACR-05 |
| Difficult receipt | receipts `cord-05` | photographed on wood grain; 0 vector ink in ScanWeave; largest receipt output |
| Aged or shaded historical | historical `history-03` | stains, decoration, Fraktur; 0 ScanWeave vector ink against heavy Adobe font use |
| Mixed artwork | mixed `scan-c03-29` | illustration plus text |
| Controlled synthetic | `qualification/clearscan_competitive` 8-page, 300 and 600 DPI | pristine truth available |

CamScanner will receive the same decoded source pixels: PNG/TIFF taken from the frozen input PDFs at their native sample grid, plus the image-only PDF where it accepts one. Any transformation the UI forces will be recorded.

## Checkpoint 2 experiments

- **E1, per-stream ledger.** Covers every comparator PDF: per-page images (dimensions, effective DPI from placement, bit depth, colour space, filters), full-page versus patch, fonts (format, glyph programs, reuse, bytes per glyph), content streams and object overhead.
- **E2, content accounting for Adobe's backgrounds and extra vector text.** Done against the source at matched geometry, covering faint rules, punctuation, stains, artwork and unsupported ink. Both PDFium and Poppler.
- **E3, font decomposition.** Glyph count against bytes per glyph and CFF against TrueType. This measures the opportunity only; no font work.
- **E4, measurement-only re-encodes of current ScanWeave residuals.** Encoded at Adobe's effective background resolution, to bound the recoverable raster bytes and show the visual cost. No product change.
- **E5, reading-size and zoomed panels.** Classified into the mission's five difference classes, plus extraction and search checks.

## Workstream C

- **C1:** PR [#28](https://github.com/mitchins/scanweave/pull/28), "Fail fast when q3 glyph sharing lacks PDFium (#27)", at `019120b`, open.
  - It checks PDFium through the same loader before any rasterization; a bad library fails in under 0.01 s with an actionable message and no output.
  - Rust tests, Python gates, hygiene, GitGuardian and CodeRabbit pass; `analyze` was still pending when this was written.
  - The reviewer independently verified that q3 output is byte-identical between `main` and the branch on two sharing-active sheets, with 2 and 8 substitutions (`8afb79d3…`, `10aaa4ae…`).
- **C2:** a measurement study on spent inputs only, running on the research branch `exp/acr06-highdpi-ownership`. Its research-only switch has no effect when unset. No production change.
