# ACR-06: guarded 150-DPI background experiment

## Recommendation and scope

**Recommendation: revise; do not open a PR.** This guard has not demonstrated a meaningful corpus saving: the observed totals are below. We did not find a guard in this experiment that both meets the page-level preservation bar and achieves a meaningful saving; this does not prove no such guard exists. Source-pixel thresholds are conservative engineering choices, not a proof of visual fidelity. Layout cost estimates remain at the existing 200-DPI setting. Auto mode and glyph sharing bypass the experiment to preserve their size-based decisions. Faithful, protected, raster-baseline, native-exception and source-JPEG paths remain on their existing representations. The document first makes the original lossless-versus-compact choice, and only then considers a smaller experimental compact PDF.

## Frozen protocol

The development split and predeclared material-regression thresholds are in [protocol.md](protocol.md). The source-pixel guard requires a maximum channel error of five levels over the full image after a 150-DPI JPEG round trip, and mean error of at most one level on horizontal source edge pairs two pixels apart and at least 20 levels apart. It requires an existing reduced representation and a smaller 150-DPI image. Every failure returns the existing image. The guard was frozen after development pages and before held-out or fresh result review. These limits are deliberately strict because the development measurements showed that counting only errors of 20 or more levels misses a material OCR loss.

The fresh generator is [fresh.py](fresh.py), seed 609150, with generator, font, truth and input hashes in [fresh-sha256.txt](fresh-sha256.txt). It uses DejaVu Serif (Bitstream Vera license; DejaVu changes public domain, `/usr/share/doc/fonts-dejavu-core/copyright`). No permissively licensed blackletter font was identified. The generator includes aged paper, 6–8 pt text, punctuation and decimal points, faint/broken print, tables, halftone and synthetic tonal artwork, at 300 DPI and a non-integer page scale. Source PNGs are the pristine raster truth; it is not photographic ground truth.

## Main release baseline

Built from `36ad4eaf4eee8084335ea5f4be3ecc2a4ab6fc2e` with `cargo build --release --locked`, `--dpi 300 --profile clearscan --glyph-sharing off`. Hashes are from the actual new main outputs; the reviewer can compare them with the post-#34 reference.

| Document | SHA-256 |
|---|---|
| financial | `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd` |
| forms | `1aa7b517618cf129b976d26aa7dd781e838bac79e96380e14b7ad74f2d0c0639` |
| historical | `8486f69c3d694c4a760ad4845c2cb6b64161467adc3e4061fef9b771b84abd2e` |
| mixed | `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a` |
| receipts | `d2da6b69bb803e6c3a5f5db0c6735f3d3357a2f84f12a98fc99fc3ef836d9360` |

Product branch `exp/acr06-bg150` is committed and pushed at `5c037d62c43c528f1a4a9af08ab8ccc4f5b77188`. No pull request was opened.

## Phase 1: unguarded 150-DPI product output

All page numbers below are one-based. The historical CP3 identifier `historical-p4` is page 5. Entries are source matched words; the source render is Tesseract English PSM 3 and counts are multisets. A dash means no qualifying whole-page DCT background was identified. Small-component survival uses source dark connected components of 2–20 pixels and a 30-level local contrast threshold. The line proxy uses 12-pixel morphological openings, and includes some text strokes. The SSIM is whole page at quarter scale; manually selected artwork crops are in `phase1-artwork-*.json`. These are proxies rather than semantic punctuation, true line classification, or a visual inspection. The PDFium and Poppler 300-DPI output render comparisons are in `phase1-render-*.json`; the source render check is in `source-renders.json`. The unguarded research build made its own complete-PDF lossless-versus-compact decision: on forms it switched the default lossless whole page to 150-DPI JPEG. Those pages are not existing reduced backgrounds and are excluded from guard calibration. The guarded implementation first preserves the default document-level choice, so this forms switch cannot occur there.

| Page | Source words | Complete default→150 | Background default→150 | Background image bytes default→150 | Small components | Survival default→150 | Rule continuity default→150 | Source SSIM default→150 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **financial** | | | | | | | | |
| 1 | 116 | 116→115 | 64→64 | 168983→107825 | 60 | 0.9500→0.8000 | 0.9876→0.9865 | 0.9961→0.9947 |
| 2 | 92 | 77→74 | 46→47 | 118923→77264 | 53 | 0.9057→0.8302 | 0.9880→0.9872 | 0.9971→0.9961 |
| 3 | 125 | 125→124 | 58→63 | 154805→101389 | 39 | 0.9744→0.8974 | 0.9878→0.9873 | 0.9968→0.9956 |
| 4 | 145 | 141→141 | 62→62 | 159351→101751 | 48 | 0.8125→0.6458 | 0.9793→0.9785 | 0.9955→0.9944 |
| 5 | 115 | 113→111 | 55→54 | 141195→92103 | 71 | 0.8451→0.7324 | 0.9863→0.9857 | 0.9970→0.9960 |
| 6 | 115 | 112→110 | 53→53 | 160726→104237 | 162 | 0.9321→0.7654 | 0.9882→0.9873 | 0.9965→0.9954 |
| 7 | 124 | 121→122 | 68→66 | 144818→95632 | 42 | 0.7619→0.6429 | 0.9885→0.9881 | 0.9967→0.9956 |
| 8 | 265 | 225→225 | 92→96 | 189804→122166 | 119 | 0.9244→0.8403 | 0.9846→0.9838 | 0.9946→0.9932 |
| 9 | 136 | 129→132 | 61→62 | 151487→97331 | 148 | 0.9122→0.7973 | 0.9880→0.9868 | 0.9962→0.9950 |
| 10 | 119 | 116→113 | 52→53 | 131041→86044 | 41 | 0.9268→0.8049 | 0.9849→0.9839 | 0.9962→0.9951 |
| 11 | 183 | 179→179 | 83→83 | 167809→110722 | 67 | 0.9552→0.8209 | 0.9837→0.9832 | 0.9959→0.9947 |
| 12 | 96 | 96→96 | 42→42 | 115613→73361 | 64 | 0.8281→0.6875 | 0.9846→0.9836 | 0.9973→0.9964 |
| 13 | 183 | 182→180 | 84→84 | 170890→110789 | 56 | 0.8750→0.6607 | 0.9839→0.9833 | 0.9957→0.9943 |
| **forms** | | | | | | | | |
| 1 | 475 | 338→291 | — | — | 153 | 0.9935→0.9477 | 0.9966→0.9950 | 0.9991→0.9923 |
| 2 | 524 | 516→422 | — | — | 391 | 1.0000→0.9668 | 0.9991→0.9983 | 0.9998→0.9893 |
| **historical** | | | | | | | | |
| 1 | 177 | 108→104 | 115→99 | 451336→265929 | 2238 | 0.5241→0.2730 | 0.9984→0.9950 | 0.9938→0.9862 |
| 2 | 113 | 89→86 | 81→82 | 306274→187752 | 549 | 0.6940→0.4153 | 0.9969→0.9946 | 0.9947→0.9877 |
| 3 | 190 | 165→148 | 163→151 | 252220→156795 | 140 | 0.6071→0.4429 | 1.0000→0.9999 | 0.9954→0.9924 |
| 4 | 60 | 27→29 | 34→29 | 629404→393114 | 1173 | 0.7519→0.5865 | 0.9999→0.9986 | 0.9959→0.9934 |
| 5 | 226 | 128→101 | 121→103 | 558993→344407 | 1418 | 0.6862→0.4965 | 0.9977→0.9960 | 0.9947→0.9887 |
| **mixed** | | | | | | | | |
| 1 | 269 | 266→259 | 159→147 | 253560→161312 | 1110 | 0.6721→0.5640 | 0.9810→0.9787 | 0.9908→0.9895 |
| 2 | 713 | 713→713 | — | — | 179 | 0.9777→0.9777 | 0.9750→0.9750 | 0.9918→0.9918 |
| **receipts** | | | | | | | | |
| 1 | 0 | 0→0 | 0→0 | 83699→52097 | 1582 | 0.4058→0.2029 | 0.9984→0.9947 | 0.9957→0.9929 |
| 2 | 7 | 0→0 | 0→0 | 66397→41615 | 836 | 0.9019→0.7344 | 0.9992→0.9965 | 0.9953→0.9925 |
| 3 | 42 | 41→41 | — | — | 26 | 1.0000→1.0000 | 0.9768→0.9768 | 0.9955→0.9955 |
| 4 | 19 | 13→9 | 14→13 | 122528→75159 | 1615 | 0.6830→0.4341 | 0.9920→0.9856 | 0.9923→0.9884 |
| 5 | 21 | 8→7 | 8→6 | 48912→31405 | 393 | 0.7684→0.6183 | 0.9992→0.9978 | 0.9958→0.9935 |
| 6 | 50 | 1→0 | 3→1 | 485445→291296 | 932 | 0.6481→0.4592 | 0.9997→0.9986 | 0.9940→0.9903 |
| 7 | 4 | 0→0 | 0→0 | 60807→37677 | 680 | 0.6426→0.4103 | 0.9992→0.9970 | 0.9949→0.9925 |
| 8 | 8 | 8→7 | 8→7 | 58362→36015 | 39 | 0.8205→0.6923 | 0.9997→0.9983 | 0.9936→0.9909 |
| 9 | 19 | 15→13 | 15→15 | 59408→36537 | 70 | 0.6714→0.5571 | 1.0000→0.9997 | 0.9952→0.9929 |
| 10 | 20 | 17→19 | 13→13 | 71595→39867 | 444 | 0.3356→0.1554 | 0.9922→0.9879 | 0.9928→0.9889 |

### Phase 1 lost and gained words

These lists are source-matched multiset differences; additional raw-token changes, image dimensions and raw values are retained in the corresponding `phase1-*.json` files.

**Predeclared unguarded flags:** financial p1 (small components); financial p2 (small components); financial p3 (small components); financial p4 (small components); financial p5 (small components); financial p6 (small components); financial p7 (small components); financial p8 (small components); financial p9 (small components); financial p10 (small components); financial p11 (small components); financial p12 (small components); financial p13 (small components); forms p1 (complete_ocr); forms p2 (complete_ocr); historical p1 (background_ocr, small components); historical p2 (small components); historical p3 (complete_ocr, background_ocr, small components); historical p4 (background_ocr, small components); historical p5 (complete_ocr, background_ocr, small components); mixed p1 (complete_ocr, background_ocr, small components); receipts p1 (small components); receipts p2 (small components); receipts p4 (complete_ocr, small components); receipts p5 (small components); receipts p6 (small components); receipts p7 (small components); receipts p8 (small components); receipts p9 (complete_ocr, small components); receipts p10 (small components). Forms flags arise from the ineligible lossless-to-JPEG research artifact described above.


**financial**

Page 1 complete: lost `Kben`; gained none.
Page 1 complete, all OCR tokens: lost `Kben`, `ss`; gained `Eben`.
Page 1 background: lost `1923`; gained `1921`.
Page 1 background, all OCR tokens: lost `1920`, `1923`; gained `1921`, `1928`.

Page 2 complete: lost `11`, `15`, `15`, `88`; gained `138`.
Page 2 complete, all OCR tokens: lost `00`, `11`, `15`, `15`, `15`, `188`, `88`; gained `138`, `iy`, `jt`, `or`.
Page 2 background: lost `15`; gained `11`, `Mazen`.
Page 2 background, all OCR tokens: lost `15`, `Hazen`, `iil`; gained `11`, `18`, `Mazen`.

Page 3 complete: lost `75`; gained none.
Page 3 complete, all OCR tokens: lost `75`; gained `175`.
Page 3 background: lost none; gained `13`, `25`, `323`, `48`, `83`.
Page 3 background, all OCR tokens: lost `3238`, `35U`; gained `13`, `25`, `323`, `350`, `48`, `83`, `os`.

Page 4 complete: lost none; gained none.
Page 4 complete, all OCR tokens: lost `Cavtella`; gained `Cactella`.
Page 4 background: lost `111`, `77`; gained `91`, `Ustate`.
Page 4 background, all OCR tokens: lost `111`, `77`, `Catella`, `ot`, `state`; gained `16`, `91`, `Cactella`, `Ustate`.

Page 5 complete: lost `HW`, `McInnis`; gained none.
Page 5 complete, all OCR tokens: lost `HW`, `McInnis`; gained `HOW`, `MeInnis`.
Page 5 background: lost `McInnis`; gained none.
Page 5 background, all OCR tokens: lost `45`, `McInnis`; gained `HOW`, `MeInnis`.

Page 6 complete: lost `52`, `57`; gained none.
Page 6 complete, all OCR tokens: lost `24812`, `52`, `53`, `57`, `AH`, `IF`, `MM`; gained `24512`, `Ba`, `HH`, `at`.
Page 6 background: lost `IPSWICH`, `TOWN`; gained `136`, `52`.
Page 6 background, all OCR tokens: lost `186`, `IPSWICH`, `TOWN`, `op`; gained `136`, `52`, `es`, `oS`.

Page 7 complete: lost `00`; gained `65`, `Wm`.
Page 7 complete, all OCR tokens: lost `00`, `Win`; gained `65`, `Wm`.
Page 7 background: lost `00`, `75`; gained none.
Page 7 background, all OCR tokens: lost `00`, `75`; gained `15`.

Page 8 complete: lost `117`, `132`, `21`, `72`, `73`, `83`; gained `121`, `128`, `17`, `85`, `85`, `Luey`.
Page 8 complete, all OCR tokens: lost `00`, `117`, `123`, `132`, `21`, `72`, `73`, `77`, `83`, `8d`, `Bones`, `Lucey`, `Tats`, `WT`, `el`, `wot`; gained `111`, `121`, `128`, `1382`, `17`, `56`, `572`, `75`, `85`, `85`, `88`, `By`, `Hil`, `Luey`, `ar`, `er`.
Page 8 background: lost `55`, `5D`, `62`, `94`; gained `113`, `117`, `17`, `73`, `73`, `78`, `97`, `99`.
Page 8 background, all OCR tokens: lost `55`, `5799`, `5D`, `62`, `75`, `94`, `TT`, `Te`, `dD`, `ee`, `el`, `ibe`, `oe`, `yee`; gained `113`, `117`, `17`, `5d`, `73`, `73`, `78`, `97`, `99`, `eae`, `ie`, `il`.

Page 9 complete: lost `97`, `Interest`; gained `1191`, `4050`, `49`, `Wi`, `on`.
Page 9 complete, all OCR tokens: lost `050`, `182340`, `97`, `Interest`, `VM`, `Wu`, `ov`, `ui`; gained `1191`, `18340`, `4050`, `49`, `Mterest`, `Wi`, `af`, `on`, `pL`.
Page 9 background: lost `49`; gained `4050`, `on`.
Page 9 background, all OCR tokens: lost `050`, `49`, `TBR`, `ov`; gained `4050`, `JE`, `on`.

Page 10 complete: lost `30000`, `IPSWICH`, `REPORT`, `TOWN`; gained `Thateh`.
Page 10 complete, all OCR tokens: lost `30000`, `95`, `IPSWICH`, `REPORT`, `TOWN`, `Thatch`; gained `30060`, `SO`, `Thateh`.
Page 10 background: lost `Thateh`; gained `Wharf`, `is`.
Page 10 background, all OCR tokens: lost `Thateh`, `Whart`; gained `Thatch`, `Wharf`, `is`.

Page 11 complete: lost `oe`; gained `99`.
Page 11 complete, all OCR tokens: lost `io`, `me`, `oe`, `thee`; gained `99`, `DD`, `aa`, `sie`.
Page 11 background: lost none; gained none.
Page 11 background, all OCR tokens: lost `mstant`; gained `mnstant`.

Page 12 complete: lost none; gained none.
Page 12 complete, all OCR tokens: lost none; gained none.
Page 12 background: lost none; gained none.
Page 12 background, all OCR tokens: lost none; gained none.

Page 13 complete: lost `27`, `280`; gained none.
Page 13 complete, all OCR tokens: lost `21`, `27`, `280`; gained `980`, `a1`, `o7`.
Page 13 background: lost `mortality`; gained `Balance`.
Page 13 background, all OCR tokens: lost `Balanee`, `mortality`; gained `Balance`, `nortality`.


**forms**

Page 1 complete: lost `12`, `16`, `18`, `212`, `26`, `48`, `500`, `52`, `62`, `700`, `ADOENDONM`, `ADORESS`, `AS10F`, `AVERY`, `BA`, `BLOCK`, `BY`, `BeCORPORATES`, `CALL`, `CFR`, `CHANGES`, `CNSCKSD`, `DBGRISH`, `DEBRA`, `DON`, `DPAS`, `Don`, `ECIFIEO`, `Eve`, `FAfS2`, `FURNISH`, `GRISHAM`, `IMS`, `INVOICES`, `Jprth`, `LESS`, `MD`, `NAMA`, `NOTATTACHED`, `NUBZONE`, `NUMMER`, `OISCOUNT`, `ONDER`, `Of`, `PRICE`, `QUANTITY`, `RATED`, `RATING`, `REFORMA`, `REMITTANCE`, `SERUICES`, `SHOWN`, `SMALL`, `SOURCE`, `STANOARO`, `STEMS`, `SUBMIT`, `SUPPLISE`, `TITLE`, `Type`, `Type`, `UNDEK`, `UNIT`, `UNIT`, `VETERAN`, `Zhe`, `andor`, `collect`, `dev`, `iS`, `oe`, `or`, `seroed`, `xs`; gained `1448`, `17`, `20`, `26104`, `2S`, `3340`, `99`, `ASD`, `CHECK`, `COOE`, `CORIPLETE`, `CUMENT`, `DUE`, `FOR`, `Fecsrds`, `METHOD`, `NAR`, `OC`, `OWNED`, `RC`, `SOUCITA`, `SOUCITANON`, `See`, `UNLESS`, `access`, `atin`, `pep`.
Page 1 complete, all OCR tokens: lost `12`, `149`, `16`, `1649`, `18`, `199`, `1S`, `20f`, `212`, `22`, `25749`, `26`, `26106`, `30L`, `3C`, `48`, `500`, `51`, `52`, `522724`, `62`, `6392`, `700`, `7N`, `7q`, `9136`, `ACOQUSINONES`, `ADOENDONM`, `ADORESS`, `AOditonal`, `AS`, `AS10F`, `ATOR`, `AVERY`, `AVWMND`, `Aaministratica`, `BA`, `BLOCK`, `BLOOX`, `BSADEY`, `BY`, `BeCORPORATES`, `BeO2`, `CALL`, `CFR`, `CHANGES`, `CHESK`, `CNSCKSD`, `CONTRACTIS`, `CONTRAST`, `CORE`, `COREPLETE`, `Ci`, `Coles`, `DBGRISH`, `DEBRA`, `DELIWERY`, `DON`, `DPAS`, `Dh`, `Don`, `ECIFIEO`, `ESE`, `Eve`, `FAfS2`, `FEKORICONTRACTOR`, `FORFOBOESTINA`, `FURNISH`, `Fecurds`, `GFFICER`, `GRISHAM`, `GUSHIES`, `HATE`, `HEQUISTDON`, `Hee`, `IMS`, `INGLUOING`, `INVOICES`, `In`, `Jprth`, `KARE`, `LESS`, `LINLESS`, `MD`, `NAMA`, `NBR`, `NC`, `NOTATTACHED`, `NUBZONE`, `NUMBOR`, `NUMMER`, `OISCOUNT`, `ONDER`, `OOCUMENT`, `OUE`, `OWED`, `Of`, `PRICE`, `QUANTITY`, `RATED`, `RATING`, `REFORMA`, `REMITTANCE`, `REO`, `REP`, `RETHEFERENT`, `S12005`, `S202`, `SCHEOULE`, `SERUICES`, `SGe`, `SHOWN`, `SIZE`, `SMALL`, `SOKITATION`, `SOLE`, `SOLER`, `SOLICITATIONICOMTRACTIOROER`, `SOUICITA`, `SOURCE`, `STANOARO`, `STEMS`, `SUBMIT`, `SUPPLISE`, `Sce`, `Spar`, `Sta`, `Stina`, `TIME`, `TISO`, `TITLE`, `TO`, `Ta`, `Type`, `Type`, `UE`, `UNDEK`, `UNIT`, `UNIT`, `VETERAN`, `Zhe`, `aa`, `accegs`, `andor`, `apieiaiatae`, `bon`, `collect`, `dev`, `ed`, `eel`, `felp`, `fio`, `ha`, `he`, `iS`, `ional`, `it`, `oe`, `oi`, `ool`, `or`, `os`, `osteo`, `panty`, `print`, `ra`, `sence`, `seroed`, `soc`, `tasn`, `tr`, `unMesTRICFe`, `vfrfry`, `ws`, `wuca`, `xs`; gained `1448`, `17`, `189`, `20`, `20749`, `2085`, `26104`, `2S`, `2S`, `301`, `31`, `31p`, `3340`, `3Be`, `522`, `52212`, `6502`, `77`, `80`, `8Y`, `99`, `ACOUSITONS`, `ADOENDOM`, `AE`, `AN`, `ANARDY`, `AOdibonal`, `AR`, `ARC`, `ASD`, `ASI0F`, `ATTACHED`, `AVERT`, `AWM`, `Adelpri`, `Aoministraticen`, `BB`, `BICORPORATES`, `BSED`, `Biock`, `CD`, `CHECK`, `CONTRACT`, `CONTRECTING`, `COOE`, `CORIPLETE`, `CS`, `CUMENT`, `DELIVERY`, `DGRISH`, `DISCOUNT`, `DUE`, `Dev`, `ED`, `Eo`, `Ev`, `FAft`, `FERCRSCONTRACTOR`, `FO`, `FOR`, `FOROESTINA`, `FURN`, `Fecsrds`, `GNATURE`, `GY`, `GYM`, `INCLUOING`, `IS`, `Jpeth`, `KITATION`, `LATE`, `Ll`, `M5`, `METHOD`, `NAME`, `NAR`, `NG`, `NGES`, `NOT`, `NR`, `NUMMIER`, `No`, `OC`, `OF`, `OFFICES`, `ON`, `OWNED`, `Occ`, `PAO`, `PY`, `Park`, `Prawns`, `Qslieue`, `RATS`, `RB`, `RC`, `RED`, `REMATTANCE`, `ROBERT`, `S2`, `SEL`, `SERVICES`, `SH`, `SINGt`, `SOLICITATIONCOMTRACTIOROER`, `SOUCITA`, `SOUCITANON`, `SPECIFIEO`, `STATES`, `SUSEIESE`, `Sebra`, `See`, `Steer`, `TAMA`, `TED`, `THE`, `THEFERENT`, `TILE`, `TRARE`, `Tadeo`, `The`, `Typeormam`, `UNLESS`, `UNLESS`, `UWESTRCFe`, `VETER`, `WSSLE`, `aS`, `access`, `ace`, `ag`, `andyor`, `at`, `atin`, `cae`, `case`, `catiect`, `coz`, `dil`, `eee`, `fTEMS`, `festa`, `fit`, `hxs`, `ig`, `in`, `ioc`, `jb`, `jp`, `mat`, `mer`, `momma`, `mye`, `na`, `om`, `ori`, `oy`, `paTe`, `pep`, `rae`, `rmmon`, `six`, `sword`, `ta`, `uaiee`, `vtfrfay`, `wana`, `we`.

Page 2 complete: lost `0002`, `10`, `12`, `13b`, `19`, `1f`, `206`, `25749`, `29749`, `2G`, `2s`, `31b`, `32`, `33490`, `515130`, `54`, `A494`, `AND`, `ARC`, `ATTACHED`, `Additonal`, `Administration`, `At`, `BIA`, `BUS`, `Beas`, `CA`, `CER`, `Contractcz`, `DATE`, `DEBRA`, `DENTIFIED`, `FOBDES`, `FOR`, `Grishan`, `INPLECTION`, `ISSUL`, `ITEM`, `In`, `LOCFL`, `Lic`, `MDB`, `NAICS`, `NAME`, `NESS`, `NO`, `NOT`, `OBERT`, `OF`, `OFFER`, `Park`, `REMITTANCE`, `SCHEDU`, `SERVICES`, `SETASIDE`, `SIGNED`, `SIZE`, `SMALL`, `SMALL`, `SRISHAM`, `STANDARD`, `SUITE`, `SUPPLIES`, `Se`, `Shests`, `St0S`, `Statement`, `This`, `UNDE`, `accordance`, `an`, `blisnees`, `catis`, `cope`, `datea`, `effecct`, `es`, `fore`, `full`, `hesting`, `in`, `jprov`, `materiel`, `or`, `pe`, `pnt`, `prnt`, `quoze`, `ris`, `sISCOUNT`, `sral`, `suservision`, `tzransporation`, `v00`, `xAR`; gained `GRFQ`.
Page 2 complete, all OCR tokens: lost `0002`, `10`, `12`, `13b`, `19`, `1f`, `206`, `25749`, `29749`, `2G`, `2s`, `31b`, `32`, `33490`, `515130`, `54`, `A494`, `AND`, `ARC`, `ATTACHED`, `Additonal`, `Administration`, `At`, `BIA`, `BUS`, `Beas`, `CA`, `CER`, `Contractcz`, `DATE`, `DEBRA`, `DENTIFIED`, `FOBDES`, `FOR`, `Grishan`, `INPLECTION`, `IRFQ`, `ISSUL`, `ITEM`, `In`, `LOCFL`, `Lic`, `MDB`, `NAICS`, `NAME`, `NESS`, `NO`, `NOT`, `OBERT`, `OF`, `OFFER`, `Park`, `REMITTANCE`, `SCHEDU`, `SERVICES`, `SETASIDE`, `SHESE`, `SIGNED`, `SIZE`, `SMALL`, `SMALL`, `SRISHAM`, `STANDARD`, `SUITE`, `SUPPLIES`, `Se`, `Shests`, `St0S`, `Statement`, `This`, `UNDE`, `accordance`, `an`, `blisnees`, `catis`, `cope`, `datea`, `effecct`, `ell`, `es`, `fore`, `full`, `hesting`, `in`, `jprov`, `materiel`, `or`, `pe`, `pnt`, `prnt`, `quoze`, `ris`, `sISCOUNT`, `sral`, `suservision`, `tate`, `tzransporation`, `v00`, `xAR`; gained `00`, `2071`, `25743`, `3349`, `3g`, `3ib`, `43b`, `4ND`, `519150`, `62`, `70R`, `92055`, `94`, `ASIDE`, `Additional`, `Adrinistraticn`, `BOSETC32`, `Bay`, `CODE`, `CODE`, `Contractcr`, `D2NTIFIED`, `Ere`, `FER`, `FORFOBDES`, `GRFQ`, `Graishan`, `INFLECTION`, `IS`, `ISSU`, `JESE`, `JNAR`, `LA`, `LOC`, `NOTATTACHED`, `OE`, `OPPS`, `RC`, `REMITTFNCE`, `ROBERT`, `S056`, `SCOUNT`, `SET`, `SUITS`, `She2ts`, `Statemenz`, `THESE`, `TOS`, `Tp`, `UNDER`, `accoraance`, `af`, `all`, `as`, `atefriel`, `calls`, `dated`, `ee`, `effecs`, `fF`, `has`, `hcszting`, `ic`, `mal`, `pani`, `prov`, `pues`, `quote`, `sn`, `supervision`, `tatc`, `too`, `transporation`, `tudes`, `ull`, `zs`.


**historical**

Page 1 complete: lost `Berolinenfiz`, `De`, `Here`, `Holte`, `Wud`, `YS`, `breit`, `brene`, `cohufs`, `den`, `dene`, `dev`, `diffe`, `ertentnis`, `fprickede`, `minem`, `miten`, `na`, `nanaen`, `oit`, `ond`, `suerft`; gained `Breffi`, `Drecke`, `Gerechs`, `Heilaudes`, `Pet`, `Sef`, `breve`, `der`, `diffem`, `fick`, `fons`, `fverens`, `gefpras`, `gegeuenys`, `if`, `landt`, `ware`, `yde`.
Page 1 complete, all OCR tokens: lost `Berolinenfiz`, `Breff`, `CHC`, `DOrecke`, `Dat`, `De`, `Det`, `Fefu`, `Gcit`, `Gefprae`, `Gereche`, `Heilandes`, `Here`, `Holte`, `Ouerfe`, `Se`, `Servordens`, `Sligen`, `VDGonte`, `WBente`, `Wud`, `YS`, `auer`, `breit`, `brene`, `breue`, `cle`, `cohufs`, `crema`, `dat`, `den`, `dene`, `denen`, `dev`, `dew`, `diffe`, `diffe`, `eines`, `en`, `ertentnis`, `fa`, `feenertennens`, `ficf`, `fiverens`, `floccty`, `fo`, `fohal`, `fprickede`, `fyrotey`, `gantgelandt`, `gegeuen`, `herude`, `ij`, `in`, `lasek`, `minem`, `miten`, `na`, `nanaen`, `nde`, `oit`, `ond`, `os`, `pa`, `prstcenicy`, `sare`, `seas`, `suerft`, `ud`, `ys`; gained `BWBente`, `Beroline`, `Biblioth`, `Breffi`, `COB`, `Datfeenertennen`, `Diffem`, `Dnd`, `Drecke`, `Gerechs`, `Gervordens`, `Greit`, `Heilaudes`, `Holre`, `Hud`, `Lasrek`, `Mere`, `Ourrfe`, `Pet`, `Regial`, `Sef`, `Sliven`, `VDBonte`, `bree`, `breve`, `che`, `clet`, `cn`, `crems`, `dae`, `de`, `de`, `de`, `deen`, `der`, `der`, `dere`, `ders`, `diffem`, `erfentnis`, `ettses`, `fick`, `flocety`, `fohatin`, `fons`, `fpricke`, `fproter`, `fverens`, `gantge`, `gefpras`, `gegeuenys`, `geitlauer`, `herudy`, `if`, `landt`, `mine`, `mit`, `namen`, `nfiZ`, `nu`, `oi`, `suerfE`, `tohufs`, `ua`, `vend`, `ware`, `yde`.
Page 1 background: lost `De`, `Here`, `Holte`, `Hundt`, `Oucefe`, `Oud`, `Wud`, `auerwunnen`, `cohufs`, `dar`, `dene`, `falfchliten`, `fick`, `frvemmende`, `fynem`, `fynt`, `herusy`, `hisfe`, `my`, `oit`, `oud`, `suerft`, `tamen`, `ticheit`, `vorteren`; gained `Gerechs`, `Heilaudes`, `Heren`, `Pet`, `Sef`, `fram`, `if`, `na`, `yde`.
Page 1 background, all OCR tokens: lost `7B`, `BerolinenfiZ`, `Bets`, `CHC`, `De`, `Dene`, `Det`, `En`, `Gereche`, `Gervordens`, `Heilandes`, `Here`, `Heven`, `Hilliges`, `Holte`, `Hundt`, `Oucefe`, `Oud`, `SE`, `Sefu`, `Seys`, `Sliven`, `Sod`, `VDGonte`, `Wud`, `auer`, `auerwunnen`, `cle`, `cohufs`, `crema`, `dar`, `dene`, `denen`, `eit`, `falfchliten`, `fampe`, `feitt`, `fick`, `fiverens`, `fleck`, `fohatin`, `fran`, `frvemmende`, `fynem`, `fynt`, `gcit`, `heffe`, `herusy`, `hisfe`, `ij`, `lasek`, `mine`, `my`, `nde`, `oit`, `oud`, `suerft`, `tamen`, `ticheit`, `ua`, `veh`, `vorteren`, `wedvderfaren`, `weltert`; gained `Berolinenfi7`, `Cnc`, `Deue`, `Deven`, `Dnd`, `Eeit`, `Fadl`, `Gerechs`, `Gerwvordens`, `Heilaudes`, `Heren`, `Hilligens`, `Hole`, `Hud`, `Hunde`, `Lasrek`, `Mere`, `Ourrfe`, `Pet`, `SS`, `See`, `Sef`, `Sn`, `Stivers`, `Te`, `WBente`, `amps`, `auertwunnen`, `cletr`, `crem`, `dat`, `de`, `dere`, `er`, `falfehliten`, `famen`, `fehal`, `fic`, `fine`, `fivemmende`, `fivereny`, `floccty`, `fram`, `fritt`, `frnens`, `geitlauer`, `hee`, `herudy`, `husje`, `if`, `in`, `mincin`, `mys`, `na`, `oi`, `ri`, `rohufs`, `se`, `suerfE`, `ta`, `tichert`, `vnd`, `voreeren`, `vty`, `wedderfaren`, `woltere`, `yde`, `ys`.

Page 2 complete: lost `PRIMYS`, `ab`, `commentarijs`, `fei`, `lili`, `materiaylpecies`, `pituram`, `tra`, `uehementer`; gained `PICT`, `Pingutore`, `VRA`, `difficiliet`, `uidebuntut`, `yi`.
Page 2 complete, all OCR tokens: lost `ISS`, `Nature`, `PRIMYS`, `PicTvRa`, `Pinguiore`, `Vf`, `Wl`, `ab`, `anemine`, `commentarijs`, `cribendo`, `difficili`, `et`, `fei`, `hos`, `lili`, `materiaylpecies`, `pituram`, `rece`, `tra`, `uehementer`, `undta`, `videbuntut`, `widerim`; gained `Illi`, `PICT`, `PRIMYyS`, `Pingutore`, `VRA`, `commeanrarijs`, `difficiliet`, `fcribendo`, `feiuncta`, `ftra`, `matcria`, `nature`, `nemin`, `pecies`, `pituramab`, `se`, `uehemenier`, `uidebuntut`, `uiderim`, `yi`.
Page 2 background: lost `alio`, `effe`, `materiaylpecies`, `piGore`, `tradita`, `uehementer`, `uncta`; gained `PICT`, `PRIMYS`, `VRA`, `commentarijs`, `cripturi`, `tra`, `ueluti`, `yi`.
Page 2 background, all OCR tokens: lost `Fy`, `PRIMVS`, `PicrvRa`, `Se`, `Sg`, `Stra`, `alio`, `anemine`, `commentartjs`, `cribendo`, `cripruri`, `eae`, `effe`, `ei`, `ki`, `materiaylpecies`, `piGore`, `principijs`, `que`, `queque`, `tradita`, `uehementer`, `uidebunturt`, `uiderim`, `uncta`, `weluti`; gained `PICT`, `PRIMYS`, `Queque`, `VRA`, `aliotradita`, `commentarijs`, `cripturi`, `east`, `efle`, `fcribendo`, `feiuncta`, `matcria`, `nemine`, `pecies`, `piGor`, `principrs`, `quee`, `tra`, `uehemenier`, `ueluti`, `videbuntut`, `widerim`, `yi`.

Page 3 complete: lost `3m`, `Danad`, `Die`, `Gd`, `Gdhinheit`, `Geift`, `Lage`, `bleibe`, `ets`, `fpridt`, `herrs`, `ic`, `ifpelt`, `ift`, `ift`, `ihr`, `jubelnd`, `nheit`, `nidt`, `nidt`; gained `Vorwelt`, `fchonen`, `jauchgt`.
Page 3 complete, all OCR tokens: lost `3m`, `Danad`, `Die`, `Dod`, `Frudjt`, `Gd`, `Gdhinheit`, `Geift`, `Gorwelf`, `Lage`, `Smweigen`, `WMenfd`, `aufiteigt`, `bleibe`, `da`, `dag`, `ets`, `fch`, `fhwsren`, `fpridt`, `herrs`, `ic`, `ifpelt`, `ift`, `ift`, `ihr`, `jauchzt`, `jubelnd`, `lade`, `mas`, `nen`, `nheit`, `nidt`, `nidt`, `tie`, `ungefaiblt`, `wmeiff`; gained `Dana`, `Dit`, `Ferudt`, `Gdinheit`, `Geist`, `Gwinheit`, `Herre`, `Sm`, `Sweigen`, `Tage`, `Vorwelt`, `Wenfd`, `aufjteigt`, `bfeibe`, `daf`, `daf`, `doch`, `ete`, `fchonen`, `fifpelt`, `fpridjt`, `fshwsren`, `ich`, `ihe`, `ijt`, `ijt`, `jauchgt`, `jube`, `ladt`, `nd`, `nidht`, `nidjt`, `twas`, `ungefable`, `weiff`, `wie`.
Page 3 background: lost `Daf`, `Dic`, `Don`, `Gdhinheit`, `Geift`, `Lerdhe`, `Natur`, `Vorwelt`, `bleibe`, `daR`, `dann`, `ein`, `ets`, `fable`, `fpridt`, `ic`, `meiff`, `nidjt`, `nidt`, `zu`; gained `3m`, `Die`, `herrs`, `hier`, `jauchgt`, `twie`, `was`, `wie`.
Page 3 background, all OCR tokens: lost `Daf`, `Dic`, `Dit`, `Don`, `Gdhinheit`, `Geift`, `Grudt`, `Guli`, `Hier`, `INorgenmwind`, `Lerdhe`, `Natur`, `Sm`, `Smeigen`, `Vorwelt`, `Wenfd`, `bleibe`, `dDanad`, `daR`, `dann`, `dev`, `ein`, `ets`, `fable`, `fcshwosren`, `fifer`, `fpridt`, `herr`, `ic`, `jauchzt`, `meiff`, `mwas`, `nidjt`, `nidt`, `tie`, `tie`, `ungefaiblt`, `zu`; gained `3m`, `Dana`, `Dann`, `Die`, `Dir`, `Frudt`, `Fuli`, `Geist`, `Ghinheit`, `Lerde`, `Matur`, `Menfd`, `Morgenwind`, `Sweigen`, `Ton`, `Vorwelf`, `bfeibe`, `cin`, `daf`, `daf`, `dec`, `ete`, `faible`, `faifer`, `fpridjt`, `fwosren`, `gu`, `herrs`, `hier`, `id`, `jauchgt`, `nicht`, `nist`, `twie`, `ungefablt`, `was`, `wei`, `wie`.

Page 4 complete: lost `Gnade`, `beweget`, `bif`; gained `Ger`, `Gott`, `Kodak`, `Shur`, `bude`.
Page 4 complete, all OCR tokens: lost `Chanight`, `Chur`, `Gnade`, `Gol`, `Her`, `Mid`, `OSGEPBERN`, `SHER`, `Sarl`, `Snidiattee`, `beweget`, `bif`, `buche`, `eticheinen7`, `ivf`, `preipivtire`, `sect`, `tangy`, `wol`; gained `Anidiatter`, `Churf`, `Ger`, `Gott`, `Hip`, `Kodak`, `Mich`, `RID`, `Sairfk`, `SendSeeBen`, `Shur`, `Tant`, `ZA`, `ag`, `ao`, `arjt`, `beweger`, `bude`, `codak`, `erfcheinenny`, `hanight`, `iw`, `nade`, `ore`, `ourdl`, `preipivttrs`, `sweet`, `wok`.
Page 4 background: lost `Digfte`, `Gnade`, `Huld`, `bif`, `ganber`, `gu`, `und`; gained `Ie`, `alg`.
Page 4 background, all OCR tokens: lost `BER`, `Buche`, `CHhanigft`, `Digfte`, `EL`, `EN`, `G2`, `Gnade`, `HEROS`, `Huld`, `Keo`, `Mairk`, `PDurchlauchtiofter`, `Pi`, `SHC`, `Snidiotter`, `Yantt`, `Zeck`, `als`, `arc`, `bif`, `erfcheinens`, `ganber`, `gegenivdrtigem`, `gu`, `mich`, `oN`, `ocr`, `preipwrr`, `und`, `wolHeflen`; gained `2mih`, `Bude`, `Geena`, `Gray`, `Hel`, `Hip`, `Ie`, `KO`, `NI`, `PDurvrchlauchtiafter`, `SPEKHSGELBEN`, `Scale`, `Snaialter`, `alg`, `antatt`, `beffen`, `cheinen7`, `ear`, `et`, `gaanber`, `gegeniwartigen`, `nade`, `preiiiwur`, `smeck`, `su`, `wol`.

Page 5 complete: lost `Doras`, `Grewiffimnea`, `Periculd`, `adbuc`, `ambBbaces`, `ame`, `atias`, `ats`, `atts`, `callertt`, `curicte`, `do2`, `dunt`, `faale`, `feinerat`, `forene`, `grammratice`, `hoc`, `huiufinoditraditide`, `in`, `infiieutto`, `legere`, `ludis`, `menfiSus`, `mibi`, `nibil`, `niclius`, `ordingqui`, `pet`, `pueris`, `quiders`, `radis`, `rudim`, `triennto`, `vin`; gained `a6`, `facili`, `facillimes`, `fact`, `fiasti`, `lingiia`, `pofteags`, `vio`.
Page 5 complete, all OCR tokens: lost `CHaleitndinie`, `CVecernBi`, `CeuAdoaquid`, `Cowuadoqnid`, `Doras`, `Fax`, `Februarie`, `Fortigs3`, `Grewiffimnea`, `Omiffi`, `Pans`, `Periculd`, `Qhusuis`, `Quo`, `Salucers`, `Sernigs`, `Spofisl`, `YoannesAuentinusttudiofis`, `aB`, `actsses`, `adbuc`, `ambBbaces`, `ame`, `atias`, `ats`, `atts`, `cCOMendare`, `cSplurs`, `callertt`, `cs`, `cumid`, `curicte`, `deBerit`, `difams`, `do2`, `dos`, `dunt`, `eidern`, `eta`, `etante`, `etrudi8us`, `eum`, `faale`, `faciat`, `facillirnes`, `facit`, `feinerat`, `fententia`, `fiast`, `firiFent`, `fiudio`, `forene`, `fquifgs`, `fulice`, `grammratice`, `hoc`, `huiufinoditraditide`, `iagta`, `in`, `in`, `incipio`, `infiieutto`, `infitn`, `insentre`, `inuentus`, `laBore`, `legere`, `lingita`, `loqut`, `ludis`, `menfiSus`, `mers`, `mibi`, `mies`, `mina`, `mrorie`, `nibil`, `niclius`, `o6fanrins`, `omnia`, `onan`, `ordingqui`, `paraBuforatiomibus`, `pet`, `pofteads`, `pueris`, `puerord`, `puetides`, `quiders`, `ra`, `radis`, `rudim`, `tamtet`, `tradiic`, `triennto`, `ullus`, `vernacila`, `videai`, `viguetts`, `vin`, `vit`, `vito`, `woes`; gained `004`, `19`, `73`, `Aullus`, `Avo`, `CHaleimdisie`, `Cdusdoquid`, `Ceusdoquid`, `Chuguis`, `ClecernBi`, `Diam`, `Dongs`, `Fabs`, `Februarys`, `Forig3`, `Grewiffinea`, `Hels`, `JoannesAuentinus`, `Omiiffi`, `Pericald`, `Saluceis`, `Ses`, `Sexwins`, `Splura`, `a6`, `acises`, `alias`, `amBbages`, `arite`, `atas`, `boc`, `cOmsendgre`, `callerit`, `cide`, `cis`, `criennto`, `cunicta`, `deBent`, `des`, `dint`, `edhucmibi`, `einerat`, `enim`, `et`, `facili`, `facillimes`, `fact`, `fade`, `falite`, `fatis`, `ferreentis`, `fiSus`, `fiasti`, `firient`, `forent`, `ftudio`, `gd`, `grammiatice`, `guider`, `huiafinodi`, `iarta`, `ifaw`, `imenire`, `infiieutio`, `inftitn`, `inventus`, `it`, `itorie`, `laBorey`, `lecrere`, `lingiia`, `loqnicumsid`, `ludic`, `me`, `men`, `meus`, `mibil`, `miclius`, `napio`, `oGfanrits`, `omnis`, `omnis`, `ordingcqui`, `partbuforatiomibus`, `per`, `pofteags`, `preri`, `puerisetrudiSus`, `pueroui`, `rndis`, `rudimeta`, `sind`, `tate`, `tr`, `tradit`, `traditise`, `ttudiolis`, `vernacula`, `videair`, `vio`, `vir`, `virquents`, `viufquifgs`, `wagers`, `xSpofisi`.
Page 5 background: lost `Seales`, `Sullus`, `adbuc`, `ame`, `atias`, `atts`, `cSmune`, `dittarat`, `etdern`, `facie`, `feinerat`, `grammratice`, `huiufinoditraditide`, `ifams`, `in`, `in`, `inflitn`, `ingenui`, `legere`, `ludis`, `mee`, `menfiSus`, `mibi`, `nibil`, `ofruant`, `princeps`, `quiders`, `radis`; gained `a6`, `etis`, `facillimes`, `fepins`, `igitur`, `noffris`, `pofteags`, `qs`, `vin`, `vtilicatenvet`.
Page 5 background, all OCR tokens: lost `004`, `13`, `74`, `Arse`, `CAaleindine`, `Cdwuadoqnid`, `ClecernGi`, `Dongs`, `FabH`, `FeSruarie`, `Fortigs`, `Grewsiffimea`, `Hers`, `Honachy`, `Pian`, `Qhusuis`, `Saluceis`, `Seales`, `Sullus`, `WPericuld`, `YoannesAuentinusitudiolis`, `aBfqs`, `actses`, `adbuc`, `ame`, `ano`, `atias`, `atts`, `auricte`, `cOmiffi`, `cOmsendgre`, `cSmune`, `came`, `ceatt`, `co4`, `ctiffinos`, `deBent`, `des`, `des`, `dittarat`, `em`, `etante`, `etdern`, `ets`, `facie`, `facillirmses`, `feinerat`, `fententia`, `fepius`, `ficati`, `fiudio`, `forenie`, `fulice`, `grammratice`, `huiufinoditraditide`, `iagta`, `ifams`, `igitnr`, `in`, `in`, `in`, `inflitn`, `ingenui`, `invents`, `itorie`, `labore`, `legere`, `lidiont`, `logntcumid`, `ludis`, `mapio`, `mee`, `menfiSus`, `mibi`, `msagno`, `nibil`, `nimirG`, `noftris`, `o6fanrins`, `ofruant`, `omnia`, `onan`, `parabuforationibus`, `pofteads`, `preternnittends`, `princeps`, `pucri`, `puerori`, `pueros`, `pueti`, `quiders`, `quifgs`, `radis`, `rdingceui`, `referuanda`, `ri`, `rndefos`, `rudimeta`, `vie`, `viguers`, `vins`, `vtilicaternvet`, `wtgemos`, `xSpofist`; gained `219`, `73`, `Aire`, `Auentinus`, `Aullus`, `CHaleimdinie`, `COnsendare`, `Causd`, `CecernBi`, `Dortee`, `Fabs`, `Forigs`, `Grewsiffinea`, `Heit`, `Honacdhyludis`, `O02`, `Otttarat`, `Pericald`, `Qhuguis`, `Quo`, `SJoannes`, `Sales`, `Salutes`, `SeSruari`, `Spofisi`, `Te`, `a6`, `acises`, `aiite`, `alias`, `alice`, `asricte`, `cOmsiffi`, `comune`, `cos`, `ctati`, `ctiffinnos`, `cudimeta`, `cunsid`, `deBerit`, `edhucmibi`, `einerat`, `eis`, `et`, `etis`, `face`, `facillimes`, `fame`, `fatis`, `feneentis`, `fepins`, `fiSus`, `fiastt`, `forent`, `fquifgs`, `ftudio`, `ftudiolis`, `gd`, `grammiatice`, `guider`, `huinfinoditraditise`, `iam`, `iarta`, `ides`, `igitur`, `inftitnedes`, `ingemui`, `int`, `inuentus`, `ironic`, `it`, `laGercy`, `lecere`, `lidion`, `loqnt`, `magne`, `me`, `men`, `mibil`, `mice`, `mnapio`, `nimird`, `noffris`, `oFruant`, `oGfenrins`, `omnis`, `oni`, `oquid`, `ordin`, `pardBuforationGus`, `pofteags`, `prerides`, `preternsittends`, `priniceps`, `prrcri`, `prreros`, `pucrous`, `qs`, `rdis`, `referuands`, `rodeos`, `tantet`, `tn`, `ui`, `vin`, `virquerts`, `viz`, `vtilicatenvet`, `wages`.


**mixed**

Page 1 complete: lost `WATSON`, `going`, `good`, `got`, `in`, `morning`, `over`, `the`; gained `tried`.
Page 1 complete, all OCR tokens: lost `Itried`, `WATSON`, `going`, `good`, `got`, `in`, `morning`, `over`, `the`; gained `WATRON`, `tried`.
Page 1 background: lost `Why`, `and`, `back`, `body`, `day`, `it`, `make`, `me`, `me`, `must`, `myself`, `no`, `off`, `on`, `praying`, `the`, `thing`; gained `but`, `could`, `she`, `too`, `why`.
Page 1 background, all OCR tokens: lost `40`, `BS`, `Jo`, `Why`, `Wis`, `Ww`, `Wye`, `a0`, `aldin`, `an`, `and`, `back`, `body`, `bus`, `cay`, `che`, `cleane`, `cow`, `cowld`, `day`, `fw`, `hely`, `ibx`, `iis`, `im`, `imt`, `io`, `it`, `lay`, `mAyRelt`, `make`, `me`, `me`, `mm`, `must`, `myself`, `no`, `noshimeg`, `off`, `on`, `ow`, `poop`, `praying`, `psy`, `sad`, `som`, `sovy`, `ss`, `the`, `thing`, `uD`, `vas`, `vas`, `vy`, `wag`, `whateva`, `wi`, `won`; gained `1b`, `1h`, `BSS`, `BY`, `Ghe`, `Giie`, `Midis`, `Sh`, `Sul`, `Wa`, `Wy`, `a5`, `aa`, `ax`, `ay`, `baal`, `but`, `clesne`, `could`, `dy`, `inyesll`, `is`, `ix`, `jos`, `lbelp`, `mest`, `mo`, `moamke`, `moe`, `moshime`, `nog`, `ny`, `of`, `ok`, `peop`, `pw`, `se`, `sere`, `she`, `son`, `sua`, `too`, `why`.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.


**receipts**

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained `HE`, `TE`, `ie`, `is`.
Page 2 background: lost none; gained none.
Page 2 background, all OCR tokens: lost none; gained `LYCHE`, `Le`, `ROWNIES`, `TE`, `ies`.

Page 3 complete: lost none; gained none.
Page 3 complete, all OCR tokens: lost none; gained none.

Page 4 complete: lost `Ades`, `Service`, `Sub`, `Total`; gained none.
Page 4 complete, all OCR tokens: lost `Ades`, `Ae`, `Ciniskei`, `Service`, `Sub`, `Total`, `Wietberee`; gained `TOTAL`, `Wietbeoes`.
Page 4 background: lost `52`, `Chicken`; gained `19`.
Page 4 background, all OCR tokens: lost `49`, `52`, `Chicken`; gained `19`, `92`, `Ghicken`.

Page 5 complete: lost `43`, `ONAN`, `VE`; gained `636`, `OND`.
Page 5 complete, all OCR tokens: lost `43`, `63`, `634`, `83`, `ASO`, `Cc`, `ON`, `ONAN`, `Onn`, `Tal`, `VE`, `bad`, `bee`; gained `636`, `93`, `DONNA`, `FASO`, `NO`, `OD`, `OND`, `ONNA`, `VEY`, `fi`, `va`.
Page 5 background: lost `OND`, `VE`, `VQ`; gained `43`.
Page 5 background, all OCR tokens: lost `434`, `DONNA`, `OND`, `ONE`, `ONNA`, `VE`, `VQ`, `oes`, `om`; gained `00`, `43`, `43`, `63`, `GRAND`, `La`, `SI`, `SONNY`, `TOTAL`, `Za`, `ow`, `va`, `wad`.

Page 6 complete: lost `Bae`; gained none.
Page 6 complete, all OCR tokens: lost `017K`, `Bae`, `GORD`, `KOE`, `ORte`, `aie`, `alinadhandiiedieenl`, `ebte`, `end`, `ied`, `ieee`, `lem`, `pent`, `wore`; gained `Ane`, `ESE`, `GAOT`, `Hens`, `Het`, `NINE`, `OFN8`, `OOS`, `SETS`, `SHEE`, `SURE`, `Saatiiedent`, `See`, `See`, `Sete`, `Stee`, `THRE`, `TOTh`, `TY`, `UneH`, `aii`, `ate`, `ceed`, `ee`, `ee`, `ee`, `eee`, `he`, `meee`, `omm`, `tee`, `tee`, `tory`, `wmOd`.
Page 6 background: lost `mee`, `ne`, `teed`; gained `Sere`.
Page 6 background, all OCR tokens: lost `17R`, `AT`, `Aine`, `BORD`, `ERE`, `GET`, `Geet`, `HE`, `HOHE`, `Hed`, `KE`, `Lede`, `ONDE`, `ORE`, `ORES`, `OnE`, `QuEh`, `Rene`, `SOND`, `Salinadhaendiiedeanl`, `Sind`, `Sint`, `TROD`, `YE`, `aeF`, `aed`, `aie`, `ee`, `ete`, `eters`, `he`, `howe`, `ieee`, `ime`, `mee`, `mime`, `mtwe`, `ne`, `oPe`, `omen`, `one`, `onee`, `teed`, `wane`, `went`, `whbe`; gained `9T`, `Gret`, `Guns`, `HOND`, `Nhe`, `ODEF`, `OE`, `OF88`, `ONE`, `Oab`, `PSE`, `Pies`, `Rete`, `SED`, `Sach`, `Sere`, `Sere`, `Solicited`, `Suet`, `TOTe`, `WAS`, `WE`, `esee`, `eter`, `ied`, `ment`, `nite`, `sree`, `tee`, `wEbP`, `wiles`.

Page 7 complete: lost none; gained none.
Page 7 complete, all OCR tokens: lost `FUN`, `Ga`, `be`; gained `HUNG`, `JA`.
Page 7 background: lost none; gained none.
Page 7 background, all OCR tokens: lost `Cc`, `Dy`, `FUNG`, `SHA`, `th`; gained `Func`, `GHA`, `LAS`.

Page 8 complete: lost `00xITEMS`; gained none.
Page 8 complete, all OCR tokens: lost `00xITEMS`; gained `000`, `000`, `000`, `13`, `300`, `300`, `33`, `33`, `36`, `50`, `700`, `O0xITEMS`.
Page 8 background: lost `00xITEMS`; gained none.
Page 8 background, all OCR tokens: lost `00xITEMS`, `eer`; gained `O0xITEMS`.

Page 9 complete: lost `1x`, `1x`, `RPO`; gained `000`.
Page 9 complete, all OCR tokens: lost `10TAL`, `1x`, `1x`, `O00`, `Pe`, `RPO`, `fe`, `pie`; gained `000`, `01AL`, `Ix`, `Ix`, `Re0`, `annie`, `wy`.
Page 9 background: lost none; gained none.
Page 9 background, all OCR tokens: lost `101AL`, `Rp0`, `aa`, `ew`, `wv`; gained `01AL`, `RpO`, `cE`.

Page 10 complete: lost none; gained `40`, `GRANDTOTAL`.
Page 10 complete, all OCR tokens: lost `gRTOT`; gained `40`, `GRANDTOTAL`.
Page 10 background: lost none; gained none.
Page 10 background, all OCR tokens: lost none; gained none.

## Historical page 5 / CP3 p4

The archived CP3 offline re-encoding reproduces 114→88 recalled words, with 37 lost and 11 gained source-matched tokens; [cp3_page4.json](cp3_page4.json) lists every token. That result re-encodes an already compressed background and is not the product experiment. In the actual product comparison the complete page falls from 128 to 101 source-matched tokens, and the background alone from 121 to 103. Examples of lost background tokens include `princeps`, `legere`, and `ingenui`; all lost and gained tokens are listed above. The new main baseline and the direct source-residual encoding differ from the older CP3 input and its double-JPEG simulation.

At 300-DPI render scale, the source thresholded-component median height was 27.0000 pixels and the estimated median skeleton stroke width 5.6569 pixels; the latter corresponds to about 2.8284 pixels at 150 DPI. Tesseract's boxes labeled as lower-case x-height letters have source median 32.0000 pixels at 300 DPI, about 16.0000 pixels at 150 DPI; blackletter misrecognition may bias this estimate. The component and skeleton measures are whole-page proxies. Mean dark contrast in the actual backgrounds changed from 92.3221 to 90.2286 levels, and mean absolute source error near dark ink changed from 7.0359 to 10.1168. Resampling and JPEG recompression plausibly soften fine strokes and introduce local ringing; the near-ink statistic also contains registration and resampling error and does not isolate ringing. Tesseract's English OCR on this blackletter is unstable, so the changed tokens are evidence of risk rather than a ground-truth transcription. Full physical proxies are in [historical-detail.json](historical-detail.json).

## Guarded qualification

| Page | Source words | Complete default→candidate | Background default→candidate | Background image bytes default→candidate | Small components | Survival default→candidate | Rule continuity default→candidate | Source SSIM default→candidate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **financial** | | | | | | | | |
| 1 | 116 | 116→116 | 64→64 | 168983→168983 | 60 | 0.9500→0.9500 | 0.9876→0.9876 | 0.9961→0.9961 |
| 2 | 92 | 77→77 | 46→46 | 118923→118923 | 53 | 0.9057→0.9057 | 0.9880→0.9880 | 0.9971→0.9971 |
| 3 | 125 | 125→125 | 58→58 | 154805→154805 | 39 | 0.9744→0.9744 | 0.9878→0.9878 | 0.9968→0.9968 |
| 4 | 145 | 141→141 | 62→62 | 159351→159351 | 48 | 0.8125→0.8125 | 0.9793→0.9793 | 0.9955→0.9955 |
| 5 | 115 | 113→113 | 55→55 | 141195→141195 | 71 | 0.8451→0.8451 | 0.9863→0.9863 | 0.9970→0.9970 |
| 6 | 115 | 112→112 | 53→53 | 160726→160726 | 162 | 0.9321→0.9321 | 0.9882→0.9882 | 0.9965→0.9965 |
| 7 | 124 | 121→121 | 68→68 | 144818→144818 | 42 | 0.7619→0.7619 | 0.9885→0.9885 | 0.9967→0.9967 |
| 8 | 265 | 225→225 | 92→92 | 189804→189804 | 119 | 0.9244→0.9244 | 0.9846→0.9846 | 0.9946→0.9946 |
| 9 | 136 | 129→129 | 61→61 | 151487→151487 | 148 | 0.9122→0.9122 | 0.9880→0.9880 | 0.9962→0.9962 |
| 10 | 119 | 116→116 | 52→52 | 131041→131041 | 41 | 0.9268→0.9268 | 0.9849→0.9849 | 0.9962→0.9962 |
| 11 | 183 | 179→179 | 83→83 | 167809→167809 | 67 | 0.9552→0.9552 | 0.9837→0.9837 | 0.9959→0.9959 |
| 12 | 96 | 96→96 | 42→42 | 115613→115613 | 64 | 0.8281→0.8281 | 0.9846→0.9846 | 0.9973→0.9973 |
| 13 | 183 | 182→182 | 84→84 | 170890→170890 | 56 | 0.8750→0.8750 | 0.9839→0.9839 | 0.9957→0.9957 |
| **forms** | | | | | | | | |
| 1 | 475 | 338→338 | — | — | 153 | 0.9935→0.9935 | 0.9966→0.9966 | 0.9991→0.9991 |
| 2 | 524 | 516→516 | — | — | 391 | 1.0000→1.0000 | 0.9991→0.9991 | 0.9998→0.9998 |
| **historical** | | | | | | | | |
| 1 | 177 | 108→108 | 115→115 | 451336→451336 | 2238 | 0.5241→0.5241 | 0.9984→0.9984 | 0.9938→0.9938 |
| 2 | 113 | 89→89 | 81→81 | 306274→306274 | 549 | 0.6940→0.6940 | 0.9969→0.9969 | 0.9947→0.9947 |
| 3 | 190 | 165→165 | 163→163 | 252220→252220 | 140 | 0.6071→0.6071 | 1.0000→1.0000 | 0.9954→0.9954 |
| 4 | 60 | 27→27 | 34→34 | 629404→629404 | 1173 | 0.7519→0.7519 | 0.9999→0.9999 | 0.9959→0.9959 |
| 5 | 226 | 128→128 | 121→121 | 558993→558993 | 1418 | 0.6862→0.6862 | 0.9977→0.9977 | 0.9947→0.9947 |
| **mixed** | | | | | | | | |
| 1 | 269 | 266→266 | 159→159 | 253560→253560 | 1110 | 0.6721→0.6721 | 0.9810→0.9810 | 0.9908→0.9908 |
| 2 | 713 | 713→713 | — | — | 179 | 0.9777→0.9777 | 0.9750→0.9750 | 0.9918→0.9918 |
| **receipts** | | | | | | | | |
| 1 | 0 | 0→0 | 0→0 | 83699→83699 | 1582 | 0.4058→0.4058 | 0.9984→0.9984 | 0.9957→0.9957 |
| 2 | 7 | 0→0 | 0→0 | 66397→66397 | 836 | 0.9019→0.9019 | 0.9992→0.9992 | 0.9953→0.9953 |
| 3 | 42 | 41→41 | — | — | 26 | 1.0000→1.0000 | 0.9768→0.9768 | 0.9955→0.9955 |
| 4 | 19 | 13→13 | 14→14 | 122528→122528 | 1615 | 0.6830→0.6830 | 0.9920→0.9920 | 0.9923→0.9923 |
| 5 | 21 | 8→8 | 8→8 | 48912→48912 | 393 | 0.7684→0.7684 | 0.9992→0.9992 | 0.9958→0.9958 |
| 6 | 50 | 1→1 | 3→3 | 485445→485445 | 932 | 0.6481→0.6481 | 0.9997→0.9997 | 0.9940→0.9940 |
| 7 | 4 | 0→0 | 0→0 | 60807→60807 | 680 | 0.6426→0.6426 | 0.9992→0.9992 | 0.9949→0.9949 |
| 8 | 8 | 8→8 | 8→8 | 58362→58362 | 39 | 0.8205→0.8205 | 0.9997→0.9997 | 0.9936→0.9936 |
| 9 | 19 | 15→15 | 15→15 | 59408→59408 | 70 | 0.6714→0.6714 | 1.0000→1.0000 | 0.9952→0.9952 |
| 10 | 20 | 17→17 | 13→13 | 71595→71595 | 444 | 0.3356→0.3356 | 0.9922→0.9922 | 0.9928→0.9928 |
| **single** | | | | | | | | |
| 1 | 269 | 266→266 | 159→159 | 253708→253708 | 1110 | 0.6712→0.6712 | 0.9811→0.9811 | 0.9908→0.9908 |
| **competitive300** | | | | | | | | |
| 1 | 10 | 4→4 | 0→0 | 10731→10731 | 0 | —→— | 0.9559→0.9559 | 0.9949→0.9949 |
| 2 | 8 | 5→5 | 0→0 | 4813→4813 | 0 | —→— | 0.9742→0.9742 | 0.9949→0.9949 |
| 3 | 8 | 6→6 | 0→0 | 4890→4890 | 0 | —→— | 0.9727→0.9727 | 0.9953→0.9953 |
| 4 | 8 | 6→6 | 0→0 | 6273→6273 | 1 | 1.0000→1.0000 | 0.9777→0.9777 | 0.9956→0.9956 |
| 5 | 8 | 6→6 | 0→0 | 4724→4724 | 0 | —→— | 0.9759→0.9759 | 0.9954→0.9954 |
| 6 | 8 | 6→6 | 0→0 | 6422→6422 | 0 | —→— | 0.9740→0.9740 | 0.9957→0.9957 |
| 7 | 8 | 7→7 | 3→3 | 19253→19253 | 1 | 1.0000→1.0000 | 0.9833→0.9833 | 0.9957→0.9957 |
| 8 | 8 | 8→8 | 6→6 | 23342→23342 | 0 | —→— | 0.9931→0.9931 | 0.9958→0.9958 |
| **competitive600** | | | | | | | | |
| 1 | 10 | 7→7 | — | — | 0 | —→— | 0.9533→0.9533 | 0.9935→0.9935 |
| 2 | 8 | 6→6 | 6→6 | 29835→29835 | 0 | —→— | 1.0000→1.0000 | 0.9959→0.9959 |
| 3 | 8 | 6→6 | 6→6 | 29842→29842 | 0 | —→— | 1.0000→1.0000 | 0.9959→0.9959 |
| 4 | 8 | 7→7 | 7→7 | 29823→29823 | 0 | —→— | 0.9999→0.9999 | 0.9960→0.9960 |
| 5 | 8 | 6→6 | 6→6 | 30096→30096 | 0 | —→— | 1.0000→1.0000 | 0.9959→0.9959 |
| 6 | 8 | 6→6 | 6→6 | 29877→29877 | 0 | —→— | 1.0000→1.0000 | 0.9960→0.9960 |
| 7 | 8 | 8→8 | 0→0 | 5938→5938 | 0 | —→— | 0.9591→0.9591 | 0.9954→0.9954 |
| 8 | 8 | 8→8 | 0→0 | 6151→6151 | 0 | —→— | 0.9576→0.9576 | 0.9949→0.9949 |
| **fresh1** | | | | | | | | |
| 1 | 259 | 259→259 | 116→116 | 438107→438107 | 2459 | 1.0000→1.0000 | 0.9815→0.9815 | 0.9873→0.9873 |
| **fresh2** | | | | | | | | |
| 1 | 259 | 259→259 | 118→118 | 459203→459203 | 2671 | 1.0000→1.0000 | 0.9764→0.9764 | 0.9882→0.9882 |
| **freshtruth1** | | | | | | | | |
| 1 | 267 | 267→267 | 139→139 | 393592→393592 | 2599 | 0.9823→0.9823 | 0.9785→0.9785 | 0.9845→0.9845 |
| **freshtruth2** | | | | | | | | |
| 1 | 267 | 267→267 | 116→116 | 384898→384898 | 2811 | 0.9932→0.9932 | 0.9664→0.9664 | 0.9837→0.9837 |

### Guard decisions and source-matched word changes

A guard log entry is the per-page decision before complete-PDF size selection. A document decision of `default` means the final PDF retained the default representation even if a preliminary page entry says 150. Missing page entries mean the experimental encoder was not invoked for that page; inspect the image and document logs rather than assuming a particular eligibility reason. The final release logs are under `local/bg150/release-verify/`.

**financial**

- `scanweave: background150 page=1 decision=fallback edge_pixels=143745 edge_error_sum=2922847 edge_error_gt5=118462 max_error=123`
- `scanweave: background150 page=2 decision=fallback edge_pixels=88598 edge_error_sum=1751013 edge_error_gt5=72019 max_error=124`
- `scanweave: background150 page=3 decision=fallback edge_pixels=122874 edge_error_sum=2464833 edge_error_gt5=100210 max_error=124`
- `scanweave: background150 page=4 decision=fallback edge_pixels=133630 edge_error_sum=2554319 edge_error_gt5=107609 max_error=136`
- `scanweave: background150 page=5 decision=fallback edge_pixels=110909 edge_error_sum=2149747 edge_error_gt5=89301 max_error=116`
- `scanweave: background150 page=6 decision=fallback edge_pixels=132954 edge_error_sum=2715065 edge_error_gt5=108033 max_error=131`
- `scanweave: background150 page=7 decision=fallback edge_pixels=115454 edge_error_sum=2246114 edge_error_gt5=92613 max_error=131`
- `scanweave: background150 page=8 decision=fallback edge_pixels=164576 edge_error_sum=3206071 edge_error_gt5=133199 max_error=120`
- `scanweave: background150 page=9 decision=fallback edge_pixels=129760 edge_error_sum=2418724 edge_error_gt5=103399 max_error=131`
- `scanweave: background150 page=10 decision=fallback edge_pixels=103699 edge_error_sum=2046000 edge_error_gt5=84537 max_error=117`
- `scanweave: background150 page=11 decision=fallback edge_pixels=145016 edge_error_sum=2895714 edge_error_gt5=119304 max_error=126`
- `scanweave: background150 page=12 decision=fallback edge_pixels=86763 edge_error_sum=1630177 edge_error_gt5=69882 max_error=118`
- `scanweave: background150 page=13 decision=fallback edge_pixels=148785 edge_error_sum=3086534 edge_error_gt5=123676 max_error=139`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.
Page 2 background: lost none; gained none.
Page 2 background, all OCR tokens: lost none; gained none.

Page 3 complete: lost none; gained none.
Page 3 complete, all OCR tokens: lost none; gained none.
Page 3 background: lost none; gained none.
Page 3 background, all OCR tokens: lost none; gained none.

Page 4 complete: lost none; gained none.
Page 4 complete, all OCR tokens: lost none; gained none.
Page 4 background: lost none; gained none.
Page 4 background, all OCR tokens: lost none; gained none.

Page 5 complete: lost none; gained none.
Page 5 complete, all OCR tokens: lost none; gained none.
Page 5 background: lost none; gained none.
Page 5 background, all OCR tokens: lost none; gained none.

Page 6 complete: lost none; gained none.
Page 6 complete, all OCR tokens: lost none; gained none.
Page 6 background: lost none; gained none.
Page 6 background, all OCR tokens: lost none; gained none.

Page 7 complete: lost none; gained none.
Page 7 complete, all OCR tokens: lost none; gained none.
Page 7 background: lost none; gained none.
Page 7 background, all OCR tokens: lost none; gained none.

Page 8 complete: lost none; gained none.
Page 8 complete, all OCR tokens: lost none; gained none.
Page 8 background: lost none; gained none.
Page 8 background, all OCR tokens: lost none; gained none.

Page 9 complete: lost none; gained none.
Page 9 complete, all OCR tokens: lost none; gained none.
Page 9 background: lost none; gained none.
Page 9 background, all OCR tokens: lost none; gained none.

Page 10 complete: lost none; gained none.
Page 10 complete, all OCR tokens: lost none; gained none.
Page 10 background: lost none; gained none.
Page 10 background, all OCR tokens: lost none; gained none.

Page 11 complete: lost none; gained none.
Page 11 complete, all OCR tokens: lost none; gained none.
Page 11 background: lost none; gained none.
Page 11 background, all OCR tokens: lost none; gained none.

Page 12 complete: lost none; gained none.
Page 12 complete, all OCR tokens: lost none; gained none.
Page 12 background: lost none; gained none.
Page 12 background, all OCR tokens: lost none; gained none.

Page 13 complete: lost none; gained none.
Page 13 complete, all OCR tokens: lost none; gained none.
Page 13 background: lost none; gained none.
Page 13 background, all OCR tokens: lost none; gained none.


**forms**

- `scanweave: background150 document decision=default reason=lossless_selected`
- `scanweave: background150 page=1 decision=fallback reason=lossless_selected`
- `scanweave: background150 page=2 decision=fallback reason=lossless_selected`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.


**historical**

- `scanweave: background150 page=1 decision=fallback edge_pixels=443293 edge_error_sum=5734366 edge_error_gt5=322619 max_error=124`
- `scanweave: background150 page=2 decision=fallback edge_pixels=380334 edge_error_sum=5140717 edge_error_gt5=267906 max_error=197`
- `scanweave: background150 page=3 decision=fallback edge_pixels=212901 edge_error_sum=774569 edge_error_gt5=48354 max_error=34`
- `scanweave: background150 page=4 decision=fallback edge_pixels=406267 edge_error_sum=1632290 edge_error_gt5=110304 max_error=56`
- `scanweave: background150 page=5 decision=fallback edge_pixels=747109 edge_error_sum=6743029 edge_error_gt5=443916 max_error=110`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.
Page 2 background: lost none; gained none.
Page 2 background, all OCR tokens: lost none; gained none.

Page 3 complete: lost none; gained none.
Page 3 complete, all OCR tokens: lost none; gained none.
Page 3 background: lost none; gained none.
Page 3 background, all OCR tokens: lost none; gained none.

Page 4 complete: lost none; gained none.
Page 4 complete, all OCR tokens: lost none; gained none.
Page 4 background: lost none; gained none.
Page 4 background, all OCR tokens: lost none; gained none.

Page 5 complete: lost none; gained none.
Page 5 complete, all OCR tokens: lost none; gained none.
Page 5 background: lost none; gained none.
Page 5 background, all OCR tokens: lost none; gained none.


**mixed**

- `scanweave: background150 page=1 decision=fallback edge_pixels=432792 edge_error_sum=2375834 edge_error_gt5=149519 max_error=57`
- `scanweave: background150 page=2 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.


**receipts**

- `scanweave: background150 page=1 decision=fallback edge_pixels=67265 edge_error_sum=473214 edge_error_gt5=32537 max_error=76`
- `scanweave: background150 page=2 decision=fallback edge_pixels=44558 edge_error_sum=245621 edge_error_gt5=17343 max_error=63`
- `scanweave: background150 page=3 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=4 decision=fallback edge_pixels=49724 edge_error_sum=455829 edge_error_gt5=30737 max_error=74`
- `scanweave: background150 page=5 decision=fallback edge_pixels=32442 edge_error_sum=142863 edge_error_gt5=8268 max_error=68`
- `scanweave: background150 page=6 decision=fallback edge_pixels=157314 edge_error_sum=915931 edge_error_gt5=67423 max_error=56`
- `scanweave: background150 page=7 decision=fallback edge_pixels=41249 edge_error_sum=337013 edge_error_gt5=19440 max_error=95`
- `scanweave: background150 page=8 decision=fallback edge_pixels=39688 edge_error_sum=327303 edge_error_gt5=21581 max_error=69`
- `scanweave: background150 page=9 decision=fallback edge_pixels=41207 edge_error_sum=140590 edge_error_gt5=7931 max_error=42`
- `scanweave: background150 page=10 decision=fallback edge_pixels=70751 edge_error_sum=764149 edge_error_gt5=47353 max_error=72`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.
Page 2 background: lost none; gained none.
Page 2 background, all OCR tokens: lost none; gained none.

Page 3 complete: lost none; gained none.
Page 3 complete, all OCR tokens: lost none; gained none.

Page 4 complete: lost none; gained none.
Page 4 complete, all OCR tokens: lost none; gained none.
Page 4 background: lost none; gained none.
Page 4 background, all OCR tokens: lost none; gained none.

Page 5 complete: lost none; gained none.
Page 5 complete, all OCR tokens: lost none; gained none.
Page 5 background: lost none; gained none.
Page 5 background, all OCR tokens: lost none; gained none.

Page 6 complete: lost none; gained none.
Page 6 complete, all OCR tokens: lost none; gained none.
Page 6 background: lost none; gained none.
Page 6 background, all OCR tokens: lost none; gained none.

Page 7 complete: lost none; gained none.
Page 7 complete, all OCR tokens: lost none; gained none.
Page 7 background: lost none; gained none.
Page 7 background, all OCR tokens: lost none; gained none.

Page 8 complete: lost none; gained none.
Page 8 complete, all OCR tokens: lost none; gained none.
Page 8 background: lost none; gained none.
Page 8 background, all OCR tokens: lost none; gained none.

Page 9 complete: lost none; gained none.
Page 9 complete, all OCR tokens: lost none; gained none.
Page 9 background: lost none; gained none.
Page 9 background, all OCR tokens: lost none; gained none.

Page 10 complete: lost none; gained none.
Page 10 complete, all OCR tokens: lost none; gained none.
Page 10 background: lost none; gained none.
Page 10 background, all OCR tokens: lost none; gained none.


**single**

- `scanweave: background150 page=1 decision=fallback edge_pixels=433824 edge_error_sum=2362148 edge_error_gt5=148918 max_error=57`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.


**competitive300**

- `scanweave: background150 page=1 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=2 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=3 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=4 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=5 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=6 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=7 decision=fallback edge_pixels=7981 edge_error_sum=218533 edge_error_gt5=6453 max_error=176`
- `scanweave: background150 page=8 decision=fallback edge_pixels=13626 edge_error_sum=342523 edge_error_gt5=10942 max_error=191`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.
Page 2 background: lost none; gained none.
Page 2 background, all OCR tokens: lost none; gained none.

Page 3 complete: lost none; gained none.
Page 3 complete, all OCR tokens: lost none; gained none.
Page 3 background: lost none; gained none.
Page 3 background, all OCR tokens: lost none; gained none.

Page 4 complete: lost none; gained none.
Page 4 complete, all OCR tokens: lost none; gained none.
Page 4 background: lost none; gained none.
Page 4 background, all OCR tokens: lost none; gained none.

Page 5 complete: lost none; gained none.
Page 5 complete, all OCR tokens: lost none; gained none.
Page 5 background: lost none; gained none.
Page 5 background, all OCR tokens: lost none; gained none.

Page 6 complete: lost none; gained none.
Page 6 complete, all OCR tokens: lost none; gained none.
Page 6 background: lost none; gained none.
Page 6 background, all OCR tokens: lost none; gained none.

Page 7 complete: lost none; gained none.
Page 7 complete, all OCR tokens: lost none; gained none.
Page 7 background: lost none; gained none.
Page 7 background, all OCR tokens: lost none; gained none.

Page 8 complete: lost none; gained none.
Page 8 complete, all OCR tokens: lost none; gained none.
Page 8 background: lost none; gained none.
Page 8 background, all OCR tokens: lost none; gained none.


**competitive600**

- `scanweave: background150 page=1 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=2 decision=fallback edge_pixels=62324 edge_error_sum=1982095 edge_error_gt5=57135 max_error=133`
- `scanweave: background150 page=3 decision=fallback edge_pixels=62168 edge_error_sum=1978418 edge_error_gt5=57033 max_error=148`
- `scanweave: background150 page=4 decision=fallback edge_pixels=67113 edge_error_sum=2209584 edge_error_gt5=61719 max_error=144`
- `scanweave: background150 page=5 decision=fallback edge_pixels=62300 edge_error_sum=1977478 edge_error_gt5=57105 max_error=133`
- `scanweave: background150 page=6 decision=fallback edge_pixels=62303 edge_error_sum=1986770 edge_error_gt5=57251 max_error=131`
- `scanweave: background150 page=7 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 page=8 decision=fallback reason=not_whole_page_background`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.

Page 2 complete: lost none; gained none.
Page 2 complete, all OCR tokens: lost none; gained none.
Page 2 background: lost none; gained none.
Page 2 background, all OCR tokens: lost none; gained none.

Page 3 complete: lost none; gained none.
Page 3 complete, all OCR tokens: lost none; gained none.
Page 3 background: lost none; gained none.
Page 3 background, all OCR tokens: lost none; gained none.

Page 4 complete: lost none; gained none.
Page 4 complete, all OCR tokens: lost none; gained none.
Page 4 background: lost none; gained none.
Page 4 background, all OCR tokens: lost none; gained none.

Page 5 complete: lost none; gained none.
Page 5 complete, all OCR tokens: lost none; gained none.
Page 5 background: lost none; gained none.
Page 5 background, all OCR tokens: lost none; gained none.

Page 6 complete: lost none; gained none.
Page 6 complete, all OCR tokens: lost none; gained none.
Page 6 background: lost none; gained none.
Page 6 background, all OCR tokens: lost none; gained none.

Page 7 complete: lost none; gained none.
Page 7 complete, all OCR tokens: lost none; gained none.
Page 7 background: lost none; gained none.
Page 7 background, all OCR tokens: lost none; gained none.

Page 8 complete: lost none; gained none.
Page 8 complete, all OCR tokens: lost none; gained none.
Page 8 background: lost none; gained none.
Page 8 background, all OCR tokens: lost none; gained none.


**fresh1**

- `scanweave: background150 page=1 decision=fallback edge_pixels=208632 edge_error_sum=5690894 edge_error_gt5=179231 max_error=118`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.


**fresh2**

- `scanweave: background150 page=1 decision=fallback edge_pixels=209749 edge_error_sum=5770734 edge_error_gt5=180848 max_error=122`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.


**freshtruth1**

- `scanweave: background150 page=1 decision=fallback edge_pixels=217444 edge_error_sum=6444074 edge_error_gt5=190400 max_error=151`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.


**freshtruth2**

- `scanweave: background150 page=1 decision=fallback edge_pixels=207415 edge_error_sum=6374167 edge_error_gt5=182895 max_error=151`
- `scanweave: background150 document decision=default`

Page 1 complete: lost none; gained none.
Page 1 complete, all OCR tokens: lost none; gained none.
Page 1 background: lost none; gained none.
Page 1 background, all OCR tokens: lost none; gained none.

## PDF bytes and preservation

| Document | Main default | Guarded | Adobe XI | Archive MRC | Saving |
|---|---:|---:|---:|---:|---:|
| financial | 2842414 | 2842414 | 718276 | 1283825 | 0 |
| forms | 831974 | 831974 | 625620 | 400384 | 0 |
| historical | 2246646 | 2246646 | 1682427 | 616324 | 0 |
| mixed | 920248 | 920248 | 235999 | 358410 | 0 |
| receipts | 1266836 | 1266836 | 915781 | 400705 | 0 |
| single | 391408 | 391408 | — | — | 0 |
| competitive300 | 200996 | 200996 | — | — | 0 |
| competitive600 | 414503 | 414503 | — | — | 0 |
| fresh1 | 475919 | 475919 | — | — | 0 |
| fresh2 | 497868 | 497868 | — | — | 0 |
| freshtruth1 | 428047 | 428047 | — | — | 0 |
| freshtruth2 | 424224 | 424224 | — | — | 0 |
| **Group total** | 8108118 | 8108118 | 4178103 | 3059648 | 0 |

### Unguarded complete-PDF sizes

| Document | Default | Unguarded 150 | Difference |
|---|---:|---:|---:|
| financial | 2842414 | 2147559 | 694855 |
| forms | 831974 | 708630 | 123344 |
| historical | 2246646 | 1396411 | 850235 |
| mixed | 920248 | 828002 | 92246 |
| receipts | 1266836 | 851344 | 415492 |

Adobe and Archive are reference outputs only. Page image streams and per-page sizes are recorded in `preservation-*.json`; the full stream classification is in `bytes.json`. PDFium and Poppler 300-DPI renderer diff statistics, raw font and content stream hashes, named image hashes, and text extraction equality are in the same preservation JSON. A whole-page rendered diff is attributed to a changed background only where all other streams match; compositing edges are included.

| Document | Font streams | Content streams | PDFium text | Poppler text | Changed image paths | qpdf | Repeat byte-identical |
|---|---|---|---|---|---:|---|---|
| financial | yes | yes | yes | yes | 0 | pass | yes |
| forms | yes | yes | yes | yes | 0 | pass | yes |
| historical | yes | yes | yes | yes | 0 | pass | yes |
| mixed | yes | yes | yes | yes | 0 | pass | yes |
| receipts | yes | yes | yes | yes | 0 | pass | yes |
| single | yes | yes | yes | yes | 0 | pass | yes |
| competitive300 | yes | yes | yes | yes | 0 | pass | yes |
| competitive600 | yes | yes | yes | yes | 0 | pass | yes |
| fresh1 | yes | yes | yes | yes | 0 | pass | yes |
| fresh2 | yes | yes | yes | yes | 0 | pass | yes |
| freshtruth1 | yes | yes | yes | yes | 0 | pass | yes |
| freshtruth2 | yes | yes | yes | yes | 0 | pass | yes |

### Page decisions, images and renderer differences

Image bytes are the sum of reachable named image streams on the page, without amortizing shared images. Renderer differences are maximum-channel absolute differences over the complete page at 300 DPI; a zero value means no rendered pixels changed.

| Document | Page | Final changed images | Decision record | Image bytes default→candidate | PDFium changed / mean / max | Poppler changed / mean / max |
|---|---:|---:|---|---:|---|---|
| financial | 1 | 0 | fallback; final default | 168983→168983 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 2 | 0 | fallback; final default | 118923→118923 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 3 | 0 | fallback; final default | 154805→154805 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 4 | 0 | fallback; final default | 159351→159351 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 5 | 0 | fallback; final default | 141195→141195 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 6 | 0 | fallback; final default | 160726→160726 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 7 | 0 | fallback; final default | 144818→144818 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 8 | 0 | fallback; final default | 189804→189804 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 9 | 0 | fallback; final default | 151487→151487 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 10 | 0 | fallback; final default | 131041→131041 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 11 | 0 | fallback; final default | 167809→167809 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 12 | 0 | fallback; final default | 115613→115613 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| financial | 13 | 0 | fallback; final default | 170890→170890 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| forms | 1 | 0 | fallback; final default | 386679→386679 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| forms | 2 | 0 | fallback; final default | 351145→351145 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| historical | 1 | 0 | fallback; final default | 451336→451336 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| historical | 2 | 0 | fallback; final default | 306274→306274 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| historical | 3 | 0 | fallback; final default | 252220→252220 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| historical | 4 | 0 | fallback; final default | 629404→629404 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| historical | 5 | 0 | fallback; final default | 558993→558993 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| mixed | 1 | 0 | fallback; final default | 253560→253560 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| mixed | 2 | 0 | fallback; final default | 256604→256604 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 1 | 0 | fallback; final default | 83699→83699 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 2 | 0 | fallback; final default | 66397→66397 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 3 | 0 | fallback; final default | 168476→168476 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 4 | 0 | fallback; final default | 122528→122528 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 5 | 0 | fallback; final default | 48912→48912 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 6 | 0 | fallback; final default | 485445→485445 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 7 | 0 | fallback; final default | 60807→60807 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 8 | 0 | fallback; final default | 58362→58362 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 9 | 0 | fallback; final default | 59408→59408 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 10 | 0 | fallback; final default | 71595→71595 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| single | 1 | 0 | fallback; final default | 253708→253708 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 1 | 0 | fallback; final default | 29613→29613 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 2 | 0 | fallback; final default | 14778→14778 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 3 | 0 | fallback; final default | 17805→17805 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 4 | 0 | fallback; final default | 12685→12685 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 5 | 0 | fallback; final default | 13363→13363 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 6 | 0 | fallback; final default | 17017→17017 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 7 | 0 | fallback; final default | 19253→19253 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive300 | 8 | 0 | fallback; final default | 23342→23342 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 1 | 0 | fallback; final default | 142370→142370 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 2 | 0 | fallback; final default | 29835→29835 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 3 | 0 | fallback; final default | 29842→29842 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 4 | 0 | fallback; final default | 29823→29823 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 5 | 0 | fallback; final default | 30096→30096 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 6 | 0 | fallback; final default | 29877→29877 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 7 | 0 | fallback; final default | 37749→37749 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| competitive600 | 8 | 0 | fallback; final default | 59880→59880 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| fresh1 | 1 | 0 | fallback; final default | 438107→438107 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| fresh2 | 1 | 0 | fallback; final default | 459203→459203 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| freshtruth1 | 1 | 0 | fallback; final default | 393592→393592 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| freshtruth2 | 1 | 0 | fallback; final default | 384898→384898 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |

Individual page review sheets and comparator references for every changed page are indexed under `local/bg150/panels/`; each index contains crop coordinates and SHA-256 hashes. Empty indices indicate no changed image stream. No independent visual review by Claude is claimed.

## Validation

The workspace Rust tests, denied-warning clippy, and Python CI logs/statuses are under `local/bg150/checks/`. The isolated Python runner uses the existing CPU-only torch installation at `/tmp/scanweave-donorfix-torch` and OTS 9.3.0. qpdf 12.4.2 requires `LD_LIBRARY_PATH=/data/coding/scanweave/tools/dist/lib`; the first checks without it failed to start (exit 127), and the fixed checks are recorded separately.

## Limits and judgment

OCR is a noisy proxy, especially for historical blackletter. Small components include noise; line openings include text and the artwork crops are manually selected. No binary claim about punctuation preservation follows from the proxy alone. Thresholds were tuned conservatively on a small, non-random development split, and the fresh pages share one generator. The frozen guard may reject many safe pages; the results do not establish that no less conservative guard could work. A smooth synthetic assembly unit test exercises acceptance, but the qualification PDFs do not provide a positive changed-page example when all guarded outputs fall back, so unchanged non-background streams in a changed full document remain unproven by this corpus. Default-to-candidate identity, where observed, directly limits the output risk for those inputs but does not prove safety on unseen inputs.

## Review sheet index hashes

| Document | Changed-page sheets | Index SHA-256 |
|---|---:|---|
| financial | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| forms | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| historical | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| mixed | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| receipts | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| single | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| competitive300 | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| competitive600 | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| fresh1 | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| fresh2 | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| freshtruth1 | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| freshtruth2 | 0 | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |

## Additional checks and decisions

| Check | Result |
|---|---|
| workspace tests | 0 (0 is success) |
| clippy | 0 (0 is success) |
| focused assembly | 0 (0 is success) |
| CLI invalid values | 0 (0 is success) |
| protected and auto mode | 0 (0 is success) |
| Python runner | 0 (0 is success) |
| faithful default vs flag | `default 0; experiment 0; identical 0` |
| main vs final product default | `financial 0; forms 0; historical 0; mixed 0; receipts 0` |
| default serialized policies | all equal; see `default-policies.json` |
| final release vs measured candidate | `run single 0; same single 0; run competitive300 0; same competitive300 0; run competitive600 0; same competitive600 0; run fresh1 0; same fresh1 0; run fresh2 0; same fresh2 0; run freshtruth1 0; same freshtruth1 0; run freshtruth2 0; same freshtruth2 0; run financial 0; same financial 0; run forms 0; same forms 0; run historical 0; same historical 0; run mixed 0; same mixed 0; run receipts 0; same receipts 0` |
| Cross-check | 12 documents, 53 pages; failures: []; see `audit.json` |
| Python gate failures | none (20 recorded) |

The source-residual instrumentation and unguarded product build can be reproduced with `build_unguarded.sh` and `unguarded.patch`. After fresh results, auto-mode containment was added to the single-image API, page-skip logging was expanded, and the false option was omitted from serialized default policy; none of those changes modified the guard. The final release outputs are compared byte for byte with the measured candidates above.

The remaining group saving is **0 bytes** across 8108118 default bytes. Historical pages 3 and 5 have material unguarded OCR regressions, and all twelve development pages have a small-component proxy decline above the predeclared threshold. These pages remain of particular concern for any future, less conservative guard.

## Independent pristine-truth fresh set

A second fresh generator, [fresh_truth.py](fresh_truth.py), seed 609151, was frozen before running these inputs; [fresh-truth-sha256.txt](fresh-truth-sha256.txt) records the generator, font, clean PNGs, damaged source PNGs and PDFs. Clean 6–8 pt text, punctuation, lines and artwork are saved independently of the simulated faint and broken source ink. The manifest contains intended text and pixel boxes. No guard change was made after reviewing the first fresh set. The following table compares each arm with that pristine truth; the component test is a threshold proxy, and OCR uses the manifest text multiset.

| Page | Arm | Truth words | Recalled | Small components | Small-component survival | Rule continuity | Artwork SSIM |
|---|---|---:|---:|---:|---:|---:|---:|
| freshtruth1 | source | 267 | 213 | 1843 | 1.0000 | 1.0000 | 0.9157 |
| freshtruth1 | default | 267 | 213 | 1843 | 1.0000 | 1.0000 | 0.8772 |
| freshtruth1 | candidate | 267 | 213 | 1843 | 1.0000 | 1.0000 | 0.8772 |
| freshtruth2 | source | 267 | 211 | 1843 | 1.0000 | 1.0000 | 0.9010 |
| freshtruth2 | default | 267 | 211 | 1843 | 1.0000 | 1.0000 | 0.8699 |
| freshtruth2 | candidate | 267 | 211 | 1843 | 1.0000 | 1.0000 | 0.8699 |

**freshtruth1: pristine-truth OCR differences**

source: truth tokens not recalled: `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`; unmatched OCR tokens: `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`.
default: truth tokens not recalled: `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`; unmatched OCR tokens: `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`.
candidate: truth tokens not recalled: `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`; unmatched OCR tokens: `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`.

**freshtruth2: pristine-truth OCR differences**

source: truth tokens not recalled: `09`, `09`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`; unmatched OCR tokens: `0S`, `0S`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`.
default: truth tokens not recalled: `09`, `09`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`; unmatched OCR tokens: `08`, `0S`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`.
candidate: truth tokens not recalled: `09`, `09`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `na`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`, `ve`; unmatched OCR tokens: `08`, `0S`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `ij`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`, `naive`.

## Artwork and photographic crops

Coordinates are normalized to the source page; these manually chosen crops are not an exhaustive artwork detector. Values compare each rendered arm with the source.

| Document | Page | Region | Crop | Default SSIM | Candidate SSIM |
|---|---:|---|---|---:|---:|
| historical (guarded) | 1 | ornament | `[0.2, 0.6, 0.85, 0.73]` | 0.9458 | 0.9458 |
| historical (guarded) | 2 | decorative initial | `[0.07, 0.22, 0.36, 0.4]` | 0.9333 | 0.9333 |
| historical (guarded) | 4 | decorative initial | `[0.22, 0.61, 0.6, 0.84]` | 0.9826 | 0.9826 |
| historical (unguarded) | 1 | ornament | `[0.2, 0.6, 0.85, 0.73]` | 0.9458 | 0.8908 |
| historical (unguarded) | 2 | decorative initial | `[0.07, 0.22, 0.36, 0.4]` | 0.9333 | 0.8595 |
| historical (unguarded) | 4 | decorative initial | `[0.22, 0.61, 0.6, 0.84]` | 0.9826 | 0.9669 |
| mixed (guarded) | 1 | illustration | `[0.02, 0.18, 0.36, 0.7]` | 0.9702 | 0.9702 |
| mixed (unguarded) | 1 | illustration | `[0.02, 0.18, 0.36, 0.7]` | 0.9702 | 0.9654 |
| receipts (guarded) | 1 | receipt photograph | `[0, 0, 1, 1]` | 0.9600 | 0.9600 |
| receipts (guarded) | 2 | receipt photograph | `[0, 0, 1, 1]` | 0.9777 | 0.9777 |
| receipts (guarded) | 3 | receipt photograph | `[0, 0, 1, 1]` | 0.9910 | 0.9910 |
| receipts (guarded) | 4 | receipt photograph | `[0, 0, 1, 1]` | 0.9632 | 0.9632 |
| receipts (guarded) | 5 | receipt photograph | `[0, 0, 1, 1]` | 0.9851 | 0.9851 |
| receipts (guarded) | 6 | receipt photograph | `[0, 0, 1, 1]` | 0.9757 | 0.9757 |
| receipts (guarded) | 7 | receipt photograph | `[0, 0, 1, 1]` | 0.9788 | 0.9788 |
| receipts (guarded) | 8 | receipt photograph | `[0, 0, 1, 1]` | 0.9765 | 0.9765 |
| receipts (guarded) | 9 | receipt photograph | `[0, 0, 1, 1]` | 0.9771 | 0.9771 |
| receipts (guarded) | 10 | receipt photograph | `[0, 0, 1, 1]` | 0.9346 | 0.9346 |
| receipts (unguarded) | 1 | receipt photograph | `[0, 0, 1, 1]` | 0.9600 | 0.9317 |
| receipts (unguarded) | 2 | receipt photograph | `[0, 0, 1, 1]` | 0.9777 | 0.9636 |
| receipts (unguarded) | 3 | receipt photograph | `[0, 0, 1, 1]` | 0.9910 | 0.9910 |
| receipts (unguarded) | 4 | receipt photograph | `[0, 0, 1, 1]` | 0.9632 | 0.9298 |
| receipts (unguarded) | 5 | receipt photograph | `[0, 0, 1, 1]` | 0.9851 | 0.9788 |
| receipts (unguarded) | 6 | receipt photograph | `[0, 0, 1, 1]` | 0.9757 | 0.9613 |
| receipts (unguarded) | 7 | receipt photograph | `[0, 0, 1, 1]` | 0.9788 | 0.9669 |
| receipts (unguarded) | 8 | receipt photograph | `[0, 0, 1, 1]` | 0.9765 | 0.9645 |
| receipts (unguarded) | 9 | receipt photograph | `[0, 0, 1, 1]` | 0.9771 | 0.9672 |
| receipts (unguarded) | 10 | receipt photograph | `[0, 0, 1, 1]` | 0.9346 | 0.8940 |
| fresh1 (guarded) | 1 | halftone and synthetic tonal artwork | `[0.05, 0.76, 0.8, 0.95]` | 0.9201 | 0.9201 |
| fresh2 (guarded) | 1 | halftone and synthetic tonal artwork | `[0.05, 0.76, 0.8, 0.95]` | 0.9547 | 0.9547 |

## Phase 1 renderer differences

The PDFium and Poppler figures below cover the whole page at 300 DPI; raw stream comparisons in the JSON identify changed image resources. The forms lossless-to-JPEG artifact is described above.

| Document | Page | Changed image streams | PDFium pixels / mean / max | Poppler pixels / mean / max |
|---|---:|---:|---|---|
| financial | 1 | 1 | 2038788 / 1.5908 / 85 | 2040282 / 1.7324 / 98 |
| financial | 2 | 1 | 1713530 / 1.1156 / 84 | 1718547 / 1.2070 / 82 |
| financial | 3 | 1 | 1940685 / 1.4935 / 88 | 1944937 / 1.6406 / 87 |
| financial | 4 | 1 | 1914887 / 1.3795 / 86 | 1917041 / 1.5137 / 86 |
| financial | 5 | 1 | 1760263 / 1.2725 / 87 | 1767552 / 1.3886 / 99 |
| financial | 6 | 1 | 2007282 / 1.4929 / 90 | 2010839 / 1.6248 / 84 |
| financial | 7 | 1 | 1836791 / 1.2920 / 81 | 1840538 / 1.4162 / 92 |
| financial | 8 | 1 | 2152608 / 1.6649 / 84 | 2155957 / 1.8321 / 94 |
| financial | 9 | 1 | 1930570 / 1.2754 / 76 | 1932943 / 1.3980 / 78 |
| financial | 10 | 1 | 1800601 / 1.2077 / 76 | 1805844 / 1.3125 / 92 |
| financial | 11 | 1 | 1931563 / 1.5175 / 86 | 1937365 / 1.6797 / 99 |
| financial | 12 | 1 | 1623258 / 1.0055 / 74 | 1631504 / 1.0972 / 79 |
| financial | 13 | 1 | 2016867 / 1.5875 / 85 | 2021961 / 1.7377 / 88 |
| forms | 1 | 1 | 2431518 / 5.0635 / 186 | 2427172 / 5.5834 / 196 |
| forms | 2 | 1 | 2570789 / 5.8406 / 182 | 2568589 / 6.2250 / 220 |
| historical | 1 | 1 | 3987402 / 4.8514 / 83 | 3987567 / 5.4959 / 92 |
| historical | 2 | 1 | 1959893 / 8.3993 / 111 | 1960237 / 9.3085 / 118 |
| historical | 3 | 1 | 3381423 / 2.2395 / 30 | 3396829 / 2.5317 / 32 |
| historical | 4 | 1 | 8230042 / 2.5462 / 33 | 8245181 / 2.7553 / 42 |
| historical | 5 | 1 | 4161230 / 4.8557 / 82 | 4164717 / 5.6965 / 82 |
| mixed | 1 | 1 | 2531035 / 2.2073 / 33 | 2548300 / 2.6329 / 34 |
| mixed | 2 | 0 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 1 | 1 | 1003738 / 2.5417 / 35 | 1004438 / 2.7305 / 46 |
| receipts | 2 | 1 | 1036819 / 2.3611 / 33 | 1036884 / 2.4684 / 41 |
| receipts | 3 | 0 | 0 / 0.0000 / 0 | 0 / 0.0000 / 0 |
| receipts | 4 | 1 | 1383967 / 2.5605 / 57 | 1386457 / 2.8180 / 64 |
| receipts | 5 | 1 | 829060 / 1.6365 / 33 | 829745 / 1.7697 / 57 |
| receipts | 6 | 1 | 7756830 / 1.8517 / 45 | 7777407 / 1.9289 / 45 |
| receipts | 7 | 1 | 922376 / 1.8764 / 56 | 925705 / 2.0231 / 66 |
| receipts | 8 | 1 | 847781 / 1.7936 / 64 | 851552 / 1.9895 / 73 |
| receipts | 9 | 1 | 1034260 / 2.1208 / 23 | 1035911 / 2.2700 / 31 |
| receipts | 10 | 1 | 915125 / 2.1425 / 62 | 916837 / 2.2657 / 64 |

## One- and two-pixel line proxy

At 300 DPI, source dark pixels in a horizontal or vertical opening at least 12 pixels long are retained only where the perpendicular five-pixel neighborhood contains at most two dark pixels. Continuity is the fraction retaining at least 20 levels of contrast against the source local-paper estimate. Text strokes and scan noise can meet this geometric rule. Unguarded values apply only to group documents.

| Document | Page | Source line pixels | Source contrast / continuity | Default contrast / continuity | Guarded contrast / continuity | Unguarded contrast / continuity |
|---|---:|---:|---|---|---|---|
| financial | 1 | 13396 | 115.0068 / 1.0000 | 92.8170 / 0.9702 | 92.8170 / 0.9702 | 83.9355 / 0.9595 |
| financial | 2 | 7591 | 109.6874 / 1.0000 | 90.5269 / 0.9731 | 90.5269 / 0.9731 | 83.2013 / 0.9635 |
| financial | 3 | 6936 | 114.6224 / 1.0000 | 93.3075 / 0.9733 | 93.3075 / 0.9733 | 85.0460 / 0.9642 |
| financial | 4 | 8994 | 111.1196 / 1.0000 | 89.8115 / 0.9612 | 89.8115 / 0.9612 | 80.5244 / 0.9496 |
| financial | 5 | 4886 | 109.8107 / 1.0000 | 85.3494 / 0.9777 | 85.3494 / 0.9777 | 74.8334 / 0.9654 |
| financial | 6 | 8300 | 112.6819 / 1.0000 | 87.8563 / 0.9705 | 87.8563 / 0.9705 | 77.1486 / 0.9560 |
| financial | 7 | 6485 | 114.5161 / 1.0000 | 89.7155 / 0.9701 | 89.7155 / 0.9701 | 81.3462 / 0.9610 |
| financial | 8 | 12253 | 111.9944 / 1.0000 | 92.4493 / 0.9625 | 92.4493 / 0.9625 | 85.0920 / 0.9521 |
| financial | 9 | 9771 | 104.2623 / 1.0000 | 84.9095 / 0.9712 | 84.9095 / 0.9712 | 78.0519 / 0.9588 |
| financial | 10 | 8991 | 106.0962 / 1.0000 | 84.4914 / 0.9647 | 84.4914 / 0.9647 | 76.6687 / 0.9535 |
| financial | 11 | 8832 | 121.4851 / 1.0000 | 96.5676 / 0.9605 | 96.5676 / 0.9605 | 88.6481 / 0.9536 |
| financial | 12 | 6716 | 111.1393 / 1.0000 | 89.5547 / 0.9663 | 89.5547 / 0.9663 | 81.7123 / 0.9549 |
| financial | 13 | 10795 | 116.5714 / 1.0000 | 93.1809 / 0.9677 | 93.1809 / 0.9677 | 84.2803 / 0.9594 |
| forms | 1 | 8858 | 145.8082 / 1.0000 | 144.6289 / 0.9801 | 144.6289 / 0.9801 | 92.8438 / 0.9422 |
| forms | 2 | 36814 | 183.3247 / 1.0000 | 182.6261 / 0.9996 | 182.6261 / 0.9996 | 116.1138 / 0.9954 |
| historical | 1 | 6751 | 64.8070 / 1.0000 | 51.0606 / 0.9745 | 51.0606 / 0.9745 | 42.3053 / 0.9153 |
| historical | 2 | 3820 | 66.4948 / 1.0000 | 55.3621 / 0.9764 | 55.3621 / 0.9764 | 47.4403 / 0.9291 |
| historical | 3 | 3270 | 38.1582 / 1.0000 | 35.7959 / 1.0000 | 35.7959 / 1.0000 | 33.3145 / 0.9985 |
| historical | 4 | 6411 | 39.8761 / 1.0000 | 36.1349 / 0.9981 | 36.1349 / 0.9981 | 33.1667 / 0.9719 |
| historical | 5 | 7549 | 61.5574 / 1.0000 | 49.5901 / 0.9656 | 49.5901 / 0.9656 | 42.9643 / 0.9200 |
| mixed | 1 | 12984 | 44.3090 / 1.0000 | 37.8787 / 0.9496 | 37.8787 / 0.9496 | 36.0059 / 0.9398 |
| mixed | 2 | 18073 | 157.0710 / 1.0000 | 144.5332 / 0.9361 | 144.5332 / 0.9361 | 144.5332 / 0.9361 |
| receipts | 1 | 2362 | 37.6887 / 1.0000 | 34.3678 / 0.9890 | 34.3678 / 0.9890 | 31.7577 / 0.9687 |
| receipts | 2 | 3188 | 43.2130 / 1.0000 | 39.3614 / 0.9969 | 39.3614 / 0.9969 | 36.2240 / 0.9868 |
| receipts | 3 | 1780 | 40.6418 / 1.0000 | 38.1991 / 0.9854 | 38.1991 / 0.9854 | 38.1991 / 0.9854 |
| receipts | 4 | 6216 | 43.5554 / 1.0000 | 37.4883 / 0.9886 | 37.4883 / 0.9886 | 33.2806 / 0.9662 |
| receipts | 5 | 2245 | 43.3876 / 1.0000 | 38.8446 / 0.9929 | 38.8446 / 0.9929 | 36.8388 / 0.9786 |
| receipts | 6 | 4217 | 36.7820 / 1.0000 | 34.6176 / 0.9943 | 34.6176 / 0.9943 | 33.0146 / 0.9815 |
| receipts | 7 | 2962 | 42.2484 / 1.0000 | 37.7386 / 0.9949 | 37.7386 / 0.9949 | 34.1252 / 0.9791 |
| receipts | 8 | 1913 | 58.8851 / 1.0000 | 49.2202 / 0.9911 | 49.2202 / 0.9911 | 43.7429 / 0.9686 |
| receipts | 9 | 419 | 36.0261 / 1.0000 | 34.4462 / 1.0000 | 34.4462 / 1.0000 | 32.9235 / 0.9928 |
| receipts | 10 | 988 | 77.7441 / 1.0000 | 63.4050 / 0.9615 | 63.4050 / 0.9615 | 58.7805 / 0.9362 |
| single | 1 | 12984 | 44.3090 / 1.0000 | 37.8589 / 0.9521 | 37.8589 / 0.9521 | — / — |
| competitive300 | 1 | 1153 | 135.8404 / 1.0000 | 123.6618 / 0.9809 | 123.6618 / 0.9809 | — / — |
| competitive300 | 2 | 466 | 161.0515 / 1.0000 | 159.3391 / 0.9721 | 159.3391 / 0.9721 | — / — |
| competitive300 | 3 | 502 | 163.1884 / 1.0000 | 157.7401 / 0.9701 | 157.7401 / 0.9701 | — / — |
| competitive300 | 4 | 517 | 153.1434 / 1.0000 | 162.4838 / 0.9691 | 162.4838 / 0.9691 | — / — |
| competitive300 | 5 | 537 | 160.2042 / 1.0000 | 165.8988 / 0.9832 | 165.8988 / 0.9832 | — / — |
| competitive300 | 6 | 487 | 160.3272 / 1.0000 | 168.3662 / 0.9774 | 168.3662 / 0.9774 | — / — |
| competitive300 | 7 | 348 | 133.8074 / 1.0000 | 134.9884 / 0.9885 | 134.9884 / 0.9885 | — / — |
| competitive300 | 8 | 358 | 137.2473 / 1.0000 | 118.3227 / 0.9972 | 118.3227 / 0.9972 | — / — |
| competitive600 | 1 | 153 | 120.7838 / 1.0000 | 122.3263 / 0.9739 | 122.3263 / 0.9739 | — / — |
| competitive600 | 2 | 46 | 125.0035 / 1.0000 | 108.4817 / 1.0000 | 108.4817 / 1.0000 | — / — |
| competitive600 | 3 | 49 | 130.9223 / 1.0000 | 115.6162 / 1.0000 | 115.6162 / 1.0000 | — / — |
| competitive600 | 4 | 71 | 145.6635 / 1.0000 | 126.8044 / 1.0000 | 126.8044 / 1.0000 | — / — |
| competitive600 | 5 | 40 | 118.9350 / 1.0000 | 104.5100 / 1.0000 | 104.5100 / 1.0000 | — / — |
| competitive600 | 6 | 43 | 120.3979 / 1.0000 | 106.1654 / 1.0000 | 106.1654 / 1.0000 | — / — |
| competitive600 | 7 | 380 | 135.5098 / 1.0000 | 139.4940 / 0.9632 | 139.4940 / 0.9632 | — / — |
| competitive600 | 8 | 372 | 144.6808 / 1.0000 | 129.0571 / 0.9274 | 129.0571 / 0.9274 | — / — |
| fresh1 | 1 | 19107 | 108.7850 / 1.0000 | 83.5791 / 0.9936 | 83.5791 / 0.9936 | — / — |
| fresh2 | 1 | 14548 | 101.5376 / 1.0000 | 81.3416 / 0.9856 | 81.3416 / 0.9856 | — / — |
| freshtruth1 | 1 | 12550 | 148.2836 / 1.0000 | 104.5672 / 0.9803 | 104.5672 / 0.9803 | — / — |
| freshtruth2 | 1 | 8709 | 132.4225 / 1.0000 | 94.5319 / 0.9642 | 94.5319 / 0.9642 | — / — |

## Independent review (Claude)

**Verdict: abandon the 150-DPI background change. Do not open a PR.** The branch `exp/acr06-bg150` (5c037d6) is kept as a record only.

- **The guard is degenerate.** It compares the 150-DPI round trip with the full-resolution source, requiring maximum channel error ≤ 5 and mean edge error ≤ 1. Any resampling breaks this, including the existing ~200-DPI encoding. On real pages the edge errors reach about 120. The guard therefore rejects every page by construction, and "0 bytes saved, 0 changed pixels" says nothing about whether a fair guard exists.
- **A fairer guard would measure the extra damage of 150 over the current ~200.** But the unguarded product evidence shows that extra damage on every real page I inspected.
  - Small-component survival drops on all 30 eligible real pages: by 0.08–0.21 on financial and by 0.15–0.25 on historical and receipts.
  - Complete-page OCR loss is material on historical p3 (165→148) and historical p5 (128→101), and present on mixed p1 (266→259) and receipts p4 (13→9).
  - Worst-region panels at 300 DPI, enlarged 2× (`review_worst_regions.py`), show visibly softer roman type on financial p6, thicker and blurred blackletter on historical p5, and faded engraving hatching on mixed p1. Receipt text is close, but the wood grain softens.
- **This corrects CP3.** CP3 called 150 DPI "visually indistinguishable", based on an offline double-JPEG simulation viewed at reading size. That claim does not hold at 2× on product output.
- **Byte opportunity measured:** the unguarded product saves 2.18 MB (27%) on the group corpus. Most of it comes from exactly the pages that degrade: historical 850 KB, financial 695 KB, receipts 415 KB.
- **No acceptable subset.** Every page with a material saving is a page with fine raster text or artwork, so no page-level subset gives a meaningful saving without visible softening.
- **The remaining gap to Adobe XI** (4.18 MB against 8.11 MB) is vector coverage, as CP3 found. It is not background resolution.

**Pre-existing defect found during review (main, not caused by this experiment):** in the default output of historical p5, several letter counters, including the "g" of "ingenui" and the "a/d" of "ad", are filled with a mid-grey blob in the page background. They are white paper in the source, and the background JPEG is the page's only layer. This has been filed as a separate issue.
