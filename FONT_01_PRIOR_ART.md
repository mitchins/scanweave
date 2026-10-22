# FONT-01 prior art and implementation choice

Research checkpoint: 23 October 2026. Product base `10b5d9318581717b45b018c3bf51b24525499295`.
These are algorithmic references, not imported implementations or pretrained assets.

| Method / primary source | Transferable idea and label | Unseen faces / cost | Availability and licensing decision |
|---|---|---|---|
| [Cutter et al., DocEng 2010](https://www.dfki.de/fileadmin/user_upload/import/4946_Cutter-Font-Reconstruction-DocEng10.pdf) | Cluster repeated tokens, then partition a proximity/co-occurrence graph into candidate fonts. Token identity and font assignment are distinct. | Unsupervised candidate fonts; sparse graph plus token comparisons. Layout alone fails on interleaved styles. | Paper available; no independently licensed reference code/weights established in this review. Implement our own constrained evidence graph, not copied paper code. |
| [Cutter et al., DRR 2011](https://www.dfki.de/web/forschung/projekte-publikationen/publikation/5011) | Extends reconstruction to assigning document characters to font clusters; distinguishes discovering templates from assigning every impression. | Multi-font document evaluation, not a claim of arbitrary unseen-font recognition. | Primary publication and PDF available; no verified redistribution-ready implementation established. Use assignment/completeness as a separate evaluation axis. |
| [Goyal et al., ACL 2020](https://aclanthology.org/2020.acl-main.266/) | Separate interpretable spatial transformations from residual inking/degradation latent variation; infer underlying glyph templates. | Unsupervised mixed-font template discovery. Generative neural fitting is materially more expensive than bounded registration. | Paper available; reusable code, pretrained weights and redistribution licence not established from the publication links. No imported assets. Start with bounded registration and explicit residual features instead of recreating the neural editor. |
| [Font-ProtoNet, CVPR Workshops 2020](https://openaccess.thecvf.com/content_CVPRW_2020/html/w34/Goel_Font-ProtoNet_Prototypical_Network-Based_Font_Identification_of_Document_Images_in_Low_CVPRW_2020_paper.html) | Learn character-image embeddings; combine support observations into font prototypes. Labels are font classes, not canonical outline IDs. | Explicit novel-font few-shot evaluation. Small encoder forward pass plus prototype distances. | Paper describes synthetic FewShot-FontID and AdobeVFR evaluation; a redistribution-ready official code/weights/data package was not verified. Do not assume the font files or AdobeVFR are freely redistributable. Independently train only on manifested local licensed fonts if justified. |
| [Ocular](https://github.com/tberg12/ocular) | Unknown-font template learning, noisy inking, baseline/spacing variation and document context. | Learns document-specific fonts; joint OCR/language inference is costly and outside this mission. | Java/Scala implementation and examples available, **GPL-3.0** (`LICENSE.txt` blob `10926e87f113fb026c366866d6fa466061562870`). Read as prior art; do not copy into MIT/Apache product. Never import its language correction as glyph identity. |
| [DeepFont](https://arxiv.org/abs/1507.03196) | Synthetic-to-real adaptation, visual font classification and compressed CNN features. | Primarily catalogue font recognition; catalogue accuracy does not establish open-set cohort safety. | Paper and described AdobeVFR data are not a verified permissively licensed deployable model bundle. No weights imported. Larger domain-adaptation architecture is unnecessary for the first baseline. |
| [Font Finder, Bui/Collomosse ICIP 2015](https://collomosse.com/pubs/Bui-ICIP-2015.pdf) | Boundary-gradient visual words, logistic regression, aggregate character evidence across a string without OCR recognition. | Per-font classifier is closed-set; pairwise registered features can be tested on unseen families. Linear scoring is cheap after feature extraction. | Primary paper available; official reusable code/weights/data licence not established. Independently implement a small pairwise linear metric, not its codebook/classifier. |
| [OmniPrint](https://github.com/SunHaozhe/OmniPrint) | Parameterized geometry and printing variation with reproducible labels. | Synthesizer, not a font classifier. Generation cost scales with observations. | Code **MIT** (license blob `ff3aa82806372aad0ba0704e21fbcf1ae1bdcfda`); bundled fonts/data have separate notices. Use its design ideas; our smaller generator records every transform and uses separately reviewed font installations. |
| [Augraphy](https://github.com/sparkfish/augraphy) | Printing/scanning degradation families beyond random dropout. | Augmentation tool; no unseen-font inference claim. Some pipelines are costly and obscure exact damage ownership. | Code **MIT** (license blob `1faa6e0306bd8b9b4e2b26f1d9573c17494ae587`). Begin with deterministic explicit degradations so structured missing-ink masks remain known. No new production dependency. |

## Chosen first implementation

1. Freeze a mixed-font benchmark and family-disjoint splits **before fitting thresholds**.
2. Compare same-character observations using bounded registration, coverage/contour,
   width/proportion and topology evidence. Do not arbitrarily deform shapes.
3. Build canonical groups using complete-link compatibility (no single-link chaining).
   Infer face cohorts separately using agreement across characters; spatial context is
   supporting evidence, never ground truth.
4. Challenge hand thresholds with a calibrated linear pairwise metric. A small CNN
   earns its cost only through held-out-family improvement at low false-merge rate.
5. Keep all normal conversion behavior unchanged until independent real-PDF validation.

Unverified code or asset licences above are explicit availability gaps, not claims
that no implementation exists. No paper's reported accuracy is a ScanWeave result.
