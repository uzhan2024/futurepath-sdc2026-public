# FuturePath Intelligence AI v2 RC4

This synthetic career-planning prototype includes profile editing, explainable deterministic matching, confirmed skill gaps, career comparison, offline practice plans, and four optional AI functions: Career Advisor, Skill Gap Coach, Learning Roadmap, and session-only Career Chat. All career requirements and profiles are fictional. Generated advice is not verified labour-market evidence. No live research, salary forecast, real CV upload, or approved O*NET data is provided.

## Release and provenance

This local release candidate reconciles RC3 (`9b9d64d4493eb4cdec8e86f83b31843445cd834e`) with the reported staging interpreter repair. Only the top-level development Run and the workflow shell task now use `.venv/bin/python`; deployment already used that interpreter. Release schema/version and this note are updated. Application, scoring, fixtures, dependency pins, license files and integrity policy are unchanged. No RC4 commit or deployed version exists. The reported Replit-only `619c2d3` was not available in the public GitHub repository when checked, so its full diff/ancestry and reported Preview checks are not independently verified here.

`FUTUREPATH_AI_V2_RC4_MANIFEST.json` records the exact runtime member names, byte sizes, and SHA-256 values. The embedded manifest excludes itself. Verify its equality with the external manifest and verify the ZIP against the separate SHA-256 sidecar. Missing, changed, extra, or unsafe runtime files must fail verification. RC3 artifacts and its original Manifest are preserved.

## Build and run

Use Python 3.11 or 3.12. The lock was installed locally on Windows Python 3.11.9 and 3.12.2; Replit/Linux compatibility remains unverified. Install only the exact pins in `requirements-public.lock` into an isolated virtual environment. AI needs no key when disabled.

```sh
python -B deployment/public_package.py verify-root
python -m venv .venv
.venv/bin/python -m pip install --no-user -r requirements-public.lock
.venv/bin/python -m streamlit run app.py --server.address=0.0.0.0 --server.port=5000 --server.headless=true
```

On Windows, use `.venv\Scripts\python.exe` for the virtual-environment interpreter. The shipped `.replit` performs integrity verification before its isolated locked build, clears pip/Python overrides, and preserves Streamlit CORS and XSRF protections. The package deliberately excludes root `requirements.txt`. Whether this suppresses Replit Autoscale's automatic installation stage requires a real Publishing Build log; it is not a documented guarantee. A local `/_stcore/health` response establishes server health only.

Create/install the isolated environment before using the development Run button. Both development paths now use the same intended interpreter as deployment. No process-kill command, automatic dependency-file removal or Manifest bypass is included.

## Staging dependency-file discrepancy

A root `requirements.txt` was reported in Replit staging, but its tracked/ignored/generated status and creator are not established by the accessible GitHub source or this local workspace. Neither the RC3/RC4 package nor its application/workflow commands create that file. The full development repository intentionally retains its own runtime requirements for local lock parity; it is not a deployment root.

Keep `verify-root` fail closed for any staging root `requirements.txt`, including an exact lock duplicate, empty file or alias. Preserve the staging file, hash and Git metadata before review; do not assume it is platform-generated and do not delete it automatically. Use an independently verified clean RC4 extraction for source comparison. Before a future authorized staging promotion, resolve provenance and preserve any reviewed file outside the publishing root, or obtain platform guidance if it is recreated. Moving a file outside the root is not proven to stop pre-build discovery. Unresolved recurrence is a publication blocker. Publishing Build remains unverified.

## Optional AI server configuration

AI defaults to disabled. Credentials belong only in server Secrets. Never place them in this package, browser fields, prompts, telemetry, or errors. A later operator must have authorization before changing Production Secrets, spending credits, or publishing.

| Environment setting | Default or requirement |
|---|---|
| `FUTUREPATH_AI_ENABLED` | `false`; explicitly enable only after all live gates pass |
| `RUNPOD_API_KEY` | Server-only credential, required for AI |
| `REDIS_URL` | Shared private TLS `rediss://` service used by every replica |
| `FUTUREPATH_AI_DAILY_BUDGET_USD` | Estimated USD `0.25` per UTC day |
| `FUTUREPATH_AI_DAILY_REQUEST_LIMIT` | `30` |
| `FUTUREPATH_AI_SESSION_REQUEST_LIMIT` | `5` per browser session per UTC day |
| `FUTUREPATH_AI_MAX_CONCURRENT` | `2`, shared across day boundaries |
| `FUTUREPATH_AI_MAX_INPUT_BYTES` | `12000` |
| `FUTUREPATH_AI_MAX_OUTPUT_TOKENS` | `700`; lower server caps apply to every request |
| `FUTUREPATH_AI_REASONING_EFFORT` | `low`; accepted configuration values: `low`, `medium`, `high` |
| `FUTUREPATH_AI_INPUT_USD_PER_MILLION` | Supplied estimate `0.77` |
| `FUTUREPATH_AI_OUTPUT_USD_PER_MILLION` | Supplied estimate `2.42` |

The provisional adapter targets competition-supplied endpoint `https://api.runpod.ai/v2/b1dd8hy2hqo1nb/openai/v1` and model `glm-5.3`. It uses non-streaming Chat Completions, a 20-second SDK timeout, no SDK retries, and at most one retry after an explicit unsupported-`reasoning_effort` 400 response. Model availability, supported efforts, usage accounting, response shape, live prices, and billing have not been verified by a paid request.

Redis URL query options and fragments are not accepted. Use the credentials/hostname/port/database URL form. The client explicitly requires certificate validation and hostname matching. Do not bypass those checks to make configuration work.

Redis atomically reserves estimated cost and checks requests, sessions, and concurrency before calls. Missing usage and failed calls retain a conservative reservation charge. This is an estimated application guard, not a provider-enforced dollar cap. Daily limits use UTC. Browser renewal can create a new session; shared request and cost limits remain necessary. The 90-second concurrency lease must exceed the verified provider request duration. All replicas must share the same Redis service and consistent configuration. Unavailable accounting blocks AI output. Real Redis Lua integration is still unverified.

## Privacy, safety, and external gates

The user separately consents before transmitting a bounded question and minimal synthetic context. Recent chat and profile edits stay in the active Streamlit session. Application usage logs contain request ID, feature, model, token counts, estimated cost, and status only. The provider filters SDK and HTTP transport loggers so debug configuration cannot emit request payloads through the pinned transport logging paths. Unknown skills are not confirmed gaps, and AI cannot change deterministic scores or approval status. Malformed or unsupported AI results fall back to the deterministic application.

Generated prose rejects external hyperlinks. Suggested chat follow-ups remain in the current session and do not trigger requests automatically. Schema and reference checks reduce unsupported output but cannot establish its factual truth.

Before public AI activation, verify the exact endpoint with an explicitly authorized small paid smoke, actual usage and reasoning accounting, current prices, provider account spending controls, and a real shared Redis service. Keep public AI disabled until these pass. Before publication, also verify the Replit Build/Run logs, anonymous HTTPS journey, WebSocket connectivity, session isolation, redacted application logs, and exact deployed source/package provenance. No public deployment or live model success is claimed by this candidate.

Licensing: see `LICENSE` and the English maintained derivative `THIRD_PARTY_NOTICES.en.md`; the original legal and historical records remain preserved in the development repository.

The complete 53-pin inventory is `RUNTIME_DEPENDENCIES.csv`. `THIRD_PARTY_RUNTIME_NOTICES.zip` retains 88 captured license/attribution files and their hashes. These cover inspected Windows distributions; upstream Streamlit license text was captured separately with normalization noted in the inventory. Bundled-component terms remain applicable. Linux wheels, frontend assets and model/platform service terms require their own review. This companion is not a blanket legal-compliance certification.
