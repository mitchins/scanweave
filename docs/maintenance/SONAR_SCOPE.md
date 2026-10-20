# Analysis scope and consolidation checkpoint

Base: main `1597671`. Zero open PRs and green CI at preflight; no closure work was manufactured. Tracked worktree clean; unrelated untracked research preserved. GitHub metadata confirms secret **name** `SONAR_TOKEN`; its value was never retrieved. Public project metadata confirms organization `mitchins`, project `mitchins_scanweave`.

## Before scope correction

Public main analysis2026-10-20T22:18:41Z:745 files,4,498,538 non-comment lines,4,501,068 total lines. Generated JSON accounts for534 files/4,486,069 non-comment lines. Other analyzed languages:206 Python files/12,157 lines;3 shell/197;1 YAML/88;1 C/27. **No Rust was analyzed.** Security E, reliability C, maintainability A; coverage absent; Quality Gate status NONE, not PASS. Snapshots and all480 unresolved issue keys/impacts are retained beside this document. The supplied dashboard category totals can overlap; they are not unique issue counts.

## Version-controlled scope

`sonar-project.properties` includes all Rust/C/Python/shell/workflow source under crates, probes, qualification and .github. It excludes generated formats by positive source-extension inclusion, not by dropping qualification directories. The maintained reference UI C utility remains included. Third-party/build/cache directories are excluded. No production Rust or maintained utility is blanket-excluded. Test files under Rust tests directories, named Python tests and contour test modules are classified as tests; inline Rust unit tests remain in their production files for analyzer handling. Generated JSON/logs/PDFs/images/fonts/archive patches and historical measurement payloads are evidence, not source code.

Rust coverage is measured with pinned cargo-llvm-cov0.9.1 and llvm-tools-preview, then imported as LCOV. No Python coverage is claimed. No untested production module is excluded from coverage. Actual server import/coverage and Quality Gate must be verified after analysis; report upload alone is insufficient. Existing tests, Clippy and Python/PDF/search CI contracts remain unchanged.

## Workflow trust and pins

Every external action uses a full verified commit SHA. `action-pins.json` records the official tagged release and repository; JavaScript actions use Node24, while dtolnay v1 is composite. Rust1.99.0 selection is distinct from the action revision. Runners are ubuntu-24.04. Repository token permissions are contents:read; checkout credentials are not persisted. Sonar jobs run only on main pushes or same-repository PRs, excluding Dependabot; the secret is supplied only to credential validation and the official scanner. No pull_request_target, secret forwarding, custom privileged checkout or token output is used. Full Git history supports blame/new-code analysis. Missing credentials fail explicitly.

Automatic analysis must be disabled in Sonar Administration → Analysis Method when adopting CI analysis. Public settings and the operator confirm automatic analysis is already disabled. No administrative setting or Quality Gate was changed. CI waits for server processing and the existing Quality Gate, without weakening it. Source-scope reductions and code remediation will be reported separately.

## Documentation and reproduction

README prose185 words (~56 seconds at200 wpm). Debian package names are present in the development environment; macOS commands use officially verified Homebrew poppler/tesseract formulae, but were not executed on a macOS host. Rust is installed with rustup and its repository toolchain file selects1.99.0. Conversion command is the existing normal CLI, not an unpublished binary distribution. All prior README technical content is preserved in `docs/DEVELOPER_GUIDE.md`; root-relative technical links were adjusted. Deferred OCR reconciliation is recorded only in LEDGER.md, not implemented.

Fresh scoped measurements, issue dispositions, review and CI results will be recorded after the first real PR analysis. No lower dashboard count is yet described as a code fix or successful Quality Gate.

First real PR CI39513352555 passed all original contracts on ef70687. Instrumented tests also passed, but LCOV writing failed because coverage/ did not exist; confirmed CodeRabbit finding4331346845. The workflow now creates that directory explicitly. Python analysis is explicitly set to the tested3.12 version. A fresh run is required; the failed report is not counted as measured coverage.

## Frozen Rust evidence correction

The first complete main scan correctly added Rust but also indexed eight archived implementation snapshots in qualification/clearscan_typography. These are rejected trial/baseline source copies, not Cargo targets or active qualification utilities. The exact eight paths and SHA-256 identities are in frozen-rust-evidence.json; only those paths are now excluded. All active Python scripts in that directory, all crates/probes Rust, tests and the C UI utility remain in scope. Their removal is an evidence-scope correction, not remediation of a production finding. No file is deleted or changed.

## Hash-locked qualification dependencies

CI installs Python dependencies from `.github/requirements-ci.txt` with both `--require-hashes` and `--only-binary=:all:`. Exact direct versions are in the adjacent `.in`; the lock includes transitive versions and official PyPI artifact SHA-256 hashes. Regenerate with Python3.12 and pip-tools7.5.3 using `CUSTOM_COMPILE_COMMAND='pip-compile --generate-hashes --strip-extras .github/requirements-ci.in' pip-compile --index-url https://pypi.org/simple --no-emit-index-url --generate-hashes --strip-extras .github/requirements-ci.in`. OTS remains9.3.0, fetched at its verified immutable upstream commit884861e0103b41d7e9845fdaf9fd1e3c12819103 and built with the same locked Meson/Ninja environment. No unpinned secondary pip install remains. LCOV is retained for seven days to inspect actual import warnings; no credentials or corpus images are uploaded.

Addresses githubactions:S8541 (AaFbZj5-2TNSduKvuG1M), S8544 (AaFbZj5-2TNSduKvuG1N), S8549 (AaFbZj5-2TNSduKvuG1O). Dependency locking does not claim to remediate unrelated source findings or change converter behavior.
