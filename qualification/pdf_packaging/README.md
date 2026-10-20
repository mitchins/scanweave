# PDF packaging and ordinary-use evidence

Product code is the ordinary `scanweave input.pdf output.pdf` path (also available under the established `scanweave-cli` binary name). It uses Poppler and real Tesseract character geometry, then the existing ClearScan implementation. `faithful` remains independently selectable. No new reconstruction profile exists.

## Reproduction

Use a Python environment with pikepdf, pypdfium2, Pillow, numpy, lxml, OCRmyPDF and archive-pdf-tools. The actual installed versions are recorded in `run-manifest.json`. External requirements: Poppler, Tesseract/language data, qpdf, OTS; `pngquant` for OCRmyPDF `-O3`. Adobe requires the existing licensed Acrobat XI Wine/Xvfb sandbox; it is not packaged here. The Adobe runner was used without modification.

1. `python3 qualification/pdf_packaging/hydrate.py` restores the losslessly packaged large JSON reports. Then `cargo build --release -p scanweave-cli`.
2. Run `serialization_ablation.py` on the frozen background PDFs; build the same 300/600 bundle inputs through `target/release/scanweave build --bundle ... --profile clearscan` (exact commands in `300/run.log`, `600/run.log` and manifests).
3. `verify_serialization.py` checks actual old/new decoded streams, geometry, extraction, native search results, fonts and matched Poppler/PDFium renders. `repeat.pdf` is the byte-identical 300 DPI rerun.
4. `prepare_corpus.py` reuses the existing CORD/OCR-D originals and downloads the documented public development sources. `run_corpus.py` makes lossless image-only shared inputs and invokes ordinary converters. These PDFs preserve original physical dimensions; CORD/OCR-D capture DPI is unknown and their geometry is nominal 300 DPI. Existing source PDF text is removed during common corpus preparation, never passed as OCR truth.
5. `run_groups.py` / `run_groups.py --adobe` convert identical multi-page collections. Single-page outputs are supplementary diagnostics; do not compare their summed font costs with Adobe's shared-font collection. `run_archive.py` and `group_archive.py` run archive-pdf-tools with CCITT masks (no lossy JBIG2 substitution).
6. `measure_real.py`, `measure_groups.py`, `refresh_search.py`, `native_inventory.py`, `atlas_control.py` and `mask_control.py` reproduce measurements. Renderer differences and failures remain separate. The atlas is a rejected representation control, not product code.

Every collection's page membership, source URLs, licences, hashes and exact run commands are recorded. `local-artifacts.json` identifies large outputs retained in the workspace but omitted from Git. `representative/` contains small reviewable examples. No sealed holdout was opened.

## Rights and attribution

CORD training receipts: Clova AI / CORD authors, CC BY 4.0, [project](https://github.com/clovaai/cord), [dataset](https://huggingface.co/datasets/naver-clova-ix/cord-v2). OCR-D pages: OCR-D contributors and source libraries, CC BY-SA 4.0; see frozen source paths and original licence. Existing provenance and licences are copied into `attribution/`.

Town of Ipswich, *Annual Report 1920*: genuine scanned financial reports, [Internet Archive](https://archive.org/details/annualreport1920ipsw), [Commons public-domain record](https://commons.wikimedia.org/wiki/File:Annual_report_(IA_annualreport1920ipsw).pdf). Thirteen fixed, distinct pages; not independent documents or a representative sample of all financial statements.

NARA, *NAMA-12-C-0002 (1940 Census)*, scanned federal procurement forms, [source](https://www.archives.gov/files/foia/pdf/1940-census.pdf), US government public-domain record. Two distinct form pages.

OCRmyPDF test resources: public-domain Project Gutenberg *Huckleberry Finn* scan (`c03-29.pdf`), and Forat Electronics (1985), LinnSequencer brochure (`linn.pdf`), CC BY-SA 3.0 / GFDL alternative. See frozen upstream `REUSE.toml` and `README.rst`. Synthetic resources discovered during source selection were excluded. `skew.pdf`, derived from the same brochure, was excluded to avoid counting a transformed duplicate as a new page.

Changes to sources: decode/render into shared image-only PDF; Tesseract OCR; conversion by each listed engine; renders and comparison crops. Derived comparison sheets containing share-alike material are distributed under **CC BY-SA 4.0** with these source attributions. Source licences continue to govern their respective images; the Rust implementation retains the repository licence.
