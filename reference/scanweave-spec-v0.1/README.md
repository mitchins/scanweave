# ScanWeave specification handoff v0.1

A coding-agent-ready design for a reusable FOSS ClearScan-style scanned-document reconstruction utility.

Start with `AGENT_BRIEF.md` for the bounded first work package. The full product/architecture/CLI contract is in `SPEC.md`; tests, metrics, corpus splits and milestone gates are in `QUALIFICATION.md`. `defaults.toml` holds proposed unqualified operating defaults. `SOURCES.md` records verified upstream building blocks and explicit verification limits.

Machine-readable input contracts are in `schemas/`. `examples/ocr-page.example.json` is a **structural illustration**, not a runnable document: its hashes are placeholders and its referenced scan is intentionally not included. JSON Schema cannot enforce cross-file hashes, affine inverses, polygon containment, Unicode byte-boundary ranges or reading-order referential integrity; those are mandatory semantic-validator tests.

This packet contains specifications and schemas only. It does not contain an implemented CLI, a benchmarked reconstruction engine, test-corpus scans, model weights or font files. Command examples describe the planned interface. Resource budgets and quality/product thresholds are proposed requirements, not measured results.

M0 must pin dependencies/toolchain, execute the small font/PDF proof and establish baselines before implementation expands. The first agent run stops after that gate. No package publication, upstream merge or release is authorized by this handoff.
