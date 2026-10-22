# ACR-02 local anatomy and recomposition

Base: ACR-01 `8f14cd329493ad0cc226e480d152d7a464fb4731` (PR15, unmerged).
No production behaviour is imported from PR14. The read-only inspector and fixed
physical-coordinate renderer are exported from PR14's exact evidence revision:

```sh
mkdir -p qualification/residual_resolution/local
git fetch origin refs/pull/14/head
git archive ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e qualification/raster_competitors | tar -x -C qualification/residual_resolution/local
```

Use the existing `qualification/.venv` and licensed development corpus. Original
CORD/OCR-D sources retain their existing attribution/licences; do not redistribute
large images. The generated DejaVu fixture is raster-only: pristine font/paper
references never enter conversion. Drawn scribbles are controlled marks, not
claimed genuine handwriting. Existing genuine NARA signatures are a separate
frozen reference. Fonts require `/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf`;
the manifest records the exact font hash. No downloaded binary release is assumed.

```sh
qualification/.venv/bin/python qualification/acr02/fixtures.py
adobe-acrobat-sandbox/clearscan.sh qualification/acr02/local/controlled-input.pdf qualification/acr02/local/controlled-adobe.pdf
qualification/.venv/bin/python qualification/acr02/anatomy.py qualification/acr02/local/controlled-adobe.pdf qualification/acr02/local/adobe-layers --pages 0,1,2,3,4,5,6,12,18,24,28,35
qualification/.venv/bin/python qualification/acr02/anatomy_summary.py
qualification/.venv/bin/python qualification/acr02/test_anatomy.py
```

The matched four-page prototype document contains controlled indices6,16,24,28.
Create it using `prepare_prototypes.py`; convert **all four pages together** using
ordinary ScanWeave and Acrobat. Real prototypes use the complete existing ACR-01
historical/financial PDFs, retaining their original document-wide donor context.

```sh
qualification/.venv/bin/python qualification/acr02/prepare_prototypes.py
cargo build --release --locked
target/release/scanweave qualification/acr02/local/prototype-input.pdf qualification/acr02/local/prototype-acr01.pdf
adobe-acrobat-sandbox/clearscan.sh qualification/acr02/local/prototype-input.pdf qualification/acr02/local/prototype-adobe.pdf
qualification/.venv/bin/python qualification/acr02/prototypes.py qualification/acr02/local/prototype-acr01.pdf qualification/acr02/local/prototype-controlled-indexed.pdf --pages 0,1,2,3 --coverage-levels 16 --foreground indexed16
qualification/.venv/bin/python qualification/acr02/prototypes.py qualification/acr02/local/prototype-acr01.pdf qualification/acr02/local/prototype-controlled-jpeg.pdf --pages 0,1,2,3 --coverage-levels 256
qualification/.venv/bin/python qualification/acr02/compare_controlled.py
qualification/.venv/bin/python qualification/acr02/verify.py
```

`prototypes.py` is a temporary derivative experiment, **not normal CLI integration**.
It isolates the already-cleaned emitted non-font page, estimates paper with a31px
maximum filter/Gaussian8, creates native coverage and150DPI foreground colour over
75DPI paper. Original font/Unicode streams and text operators remain. Existing
raster-only text must survive in the coverage/colour layers, independently of OCR.
Results show why this candidate is not promoted; see root reports. Real commands
and output identities are in `run-manifest.json` and the local logs/JSON sidecars.

Ablation uses original CTMs, clipping and transparency. `all` is an ordered replay
checked pixel-identical in both engines; isolated RGB views are **not** algebraically
additive. Individual image views retain their parent masks. A mask is selection,
not independently painted content. Inline images are additionally isolated as an
ordered collective; they are not mislabeled as independently addressed XObjects.
Text clipping/stroking modes fail explicitly. Derivatives retain full context but
only the selected page is qualified. Never overwrite frozen PDFs.
