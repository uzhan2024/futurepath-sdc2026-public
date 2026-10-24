# FuturePath Intelligence V3 RC2

FuturePath includes sample profiles and explicitly confirmed user skill states, explainable deterministic matching against fictional occupation requirements, gap analysis, comparison and practice plans. Local Ollama adds Career Advisor, Skill Gap Coach, Learning Roadmap, Chat and an optional local resume draft. No generated suggestion becomes a skill assertion without user confirmation. Occupation data remains synthetic; there is no live job research, salary forecast or approved O*NET/OpenAlex data.

## Release and provenance

This V3 RC2 artifact is prepared from reviewed, allow-listed source on `development/v3-20261024`, based on development commit `aaa1a6c9afc2396b85b9d94fa224d6c326eb6e39`. Its sanitized predecessor is V3 RC1 commit `6e7a8d430a43031dabf401efb9bfa63c609943df`. RC2 retains the existing Ollama, confirmed-profile, English UI and local CV implementation, and adds the reviewed RunPod safety limits/retry controls and canonical LF release controls. Matching arithmetic, fixtures and all 55 dependency pins are unchanged. Record the new candidate source commit separately with the exact artifact hashes. Previous stable production and all historical artifacts remain preserved. Local engineering evidence is not a production deployment claim.

`FUTUREPATH_V3_RC2_MANIFEST.json` records exact source members, sizes and hashes. It excludes itself. Compare it with the external Manifest and ZIP SHA-256 sidecar. Root preflight rejects missing/altered/extra source files, including Agent memory and root requirements, while excluding only Git metadata, the installed `.venv` and bytecode-cache directories from source enumeration. Runtime environment contents still require independent inspection; they are not covered by source hashes.

The Manifest includes `.gitattributes`. Its reviewed policy forces `.replit` and `.gitattributes` to UTF-8 LF without BOM. Other members use `-text` to preserve their exact bytes during Git checkout, independent of `core.autocrlf`. Build, ZIP verification and root preflight reject CRLF control files or a changed attributes policy even if someone regenerates hashes. Do not repair a failed preflight by refreshing the Manifest in Replit. Release builds refuse to overwrite an existing ZIP or sidecar.

## Build and run

Use Python 3.11 or 3.12 and install exact pins from `requirements-public.lock` into an isolated environment. Local development defaults to installed Ollama model `qwen3.5:4b` at `http://127.0.0.1:11434`. No cloud key or Redis is needed for local Ollama. No model is automatically downloaded. Without a reachable model, use manual profiles and rule-based practice.

```sh
python -B deployment/public_package.py verify-root
python -m venv .venv
.venv/bin/python -m pip install --no-user -r requirements-public.lock
.venv/bin/python -m streamlit run app.py --server.address=0.0.0.0 --server.port=5000 --server.headless=true
```

On Windows, use `.venv\Scripts\python.exe` for the virtual-environment interpreter. The shipped `.replit` performs integrity verification before its isolated locked build, clears pip/Python overrides, and preserves Streamlit CORS and XSRF protections. The package deliberately excludes root `requirements.txt`. Whether this suppresses Replit Autoscale's automatic installation stage requires a real Publishing Build log; it is not a documented guarantee. A local `/_stcore/health` response establishes server health only.

The shipped Replit commands explicitly set public mode, AI disabled and CV disabled. Both development Run paths and Production Run use `.venv/bin/python`. Local Windows uses `.venv\Scripts\python.exe`; its environment can override provider settings for local work. Do not expose the unauthenticated Ollama service outside loopback. No automatic process termination or dependency-file cleanup is included.

## Staging dependency-file discrepancy

The owner confirmed Agent additions in Replit-local `619c2d3` and a Run fix in `0add62a`. Those additions are excluded from sanitized releases. Preserve that history privately when switching Staging; do not merge the Agent branch or delete unknown untracked work. Development retains its own root requirements for lock parity and must not be deployed as a source root.

Keep `verify-root` fail closed for any staging root `requirements.txt`, including an exact lock duplicate, empty file or alias. Preserve its bytes/history; do not automatically delete it or assume any new recurrence is platform-generated. Compare with a clean V3 extraction. Obtain platform guidance if it is recreated before the custom Build. A custom cleanup cannot fix a failure before that command. Publishing Build remains unverified.

## Local resume privacy and limits

Resume import is disabled in public mode, including Replit. It supports English text PDF/DOCX up to 2 MB, 10 PDF pages and 12,000 extracted text bytes. Scans/OCR, encrypted PDFs, macros/embeddings, unsafe ZIPs, oversized/complex documents and parser failures fall back to manual entry. Parsing uses a child process with a 512 MB memory ceiling, 12-second parent deadline and Linux CPU limit. These limits reduce resource risk; this is not a malware-analysis sandbox.

CV inference is partially validated. Short fictional resume extraction succeeded locally; a longer fictional 2,185-byte text case failed strict validation twice. Arbitrary realistic resumes and complete multi-chunk extraction are not release-proven. No real resumes were used in these tests. Manual entry remains the supported fallback.

No application file, database, prompt log or cross-session cache stores a resume. Common contact patterns are minimized before local extraction, but this is not guaranteed PII anonymization. The local model selects quotes, the server verifies literal source support, and controlled vocabulary maps mentions to unconfirmed skill suggestions. Neither extraction nor a mention proves proficiency. Users explicitly choose states before applying them to matching. Background claims never change scores.

Clear removes application draft state and rotates the upload control. Confirmed skill choices remain in the user's profile; resetting those is separate. Streamlit/OS/model-host upload buffers, logs, swap or process memory may persist until their own cleanup; secure physical erasure is not guaranteed. Review local Ollama logging/binding. There is no cloud-CV route or automatic cloud fallback. Model output remains untrusted; failed validation leaves the deterministic app available.

## Provider configuration

`FUTUREPATH_AI_PROVIDER` accepts `ollama`, `runpod`, `disabled`, or test-only `mock` (explicit dependency injection; never real app inference). Local default is Ollama; public default is disabled. `FUTUREPATH_OLLAMA_URL` must be an explicit HTTP loopback address/port without credentials, paths or redirects. `FUTUREPATH_OLLAMA_MODEL` selects an already installed local model. Local inference uses one process-wide concurrent slot and a bounded per-session request window; those are local resource controls, not distributed cloud protection. JSON Schema requests are followed by strict server validation. Full responses are validated before display; partial streaming is deliberately not exposed.

The runtime inventory has 55 pins (7 direct, 48 transitive) and 90 retained attribution captures. The two new dependencies are pypdf 6.21.2 and defusedxml 0.7.1; previous pins remain unchanged. Actual Linux wheels/licensing and Replit Publishing require their own release evidence.

## Optional AI server configuration

Public AI defaults to disabled. Local Ollama needs no cloud credential. For a separately authorized future RunPod deployment, credentials belong only in server Secrets. Never place them in this package, browser fields, prompts, telemetry, or errors. A later operator must have authorization before changing Production Secrets, spending credits, or publishing. The shipped Replit Run commands force AI off; enabling cloud AI therefore requires a reviewed new configuration release as well as Secrets.

| Environment setting | Default or requirement |
|---|---|
| `FUTUREPATH_AI_ENABLED` | `false`; explicitly enable only after all live gates pass |
| `RUNPOD_API_KEY` | Server-only credential, required for AI |
| `REDIS_URL` | Shared private TLS `rediss://` service used by every replica |
| `FUTUREPATH_AI_DAILY_BUDGET_USD` | Estimated USD `0.10` per UTC day |
| `FUTUREPATH_AI_DAILY_REQUEST_LIMIT` | `10` |
| `FUTUREPATH_AI_SESSION_REQUEST_LIMIT` | `3` per browser session per UTC day |
| `FUTUREPATH_AI_MAX_CONCURRENT` | `1`, shared across day boundaries |
| `FUTUREPATH_AI_MAX_INPUT_BYTES` | `8000` |
| `FUTUREPATH_AI_MAX_OUTPUT_TOKENS` | `512`; lower server caps apply to every request |
| `FUTUREPATH_AI_REASONING_EFFORT` | `low`; accepted configuration values: `low`, `medium`, `high` |
| `FUTUREPATH_AI_INPUT_USD_PER_MILLION` | Supplied estimate `0.77` |
| `FUTUREPATH_AI_OUTPUT_USD_PER_MILLION` | Supplied estimate `2.42` |

The adapter targets competition-supplied endpoint `https://api.runpod.ai/v2/b1dd8hy2hqo1nb/openai/v1` and request model `glm-5.3`. One owner-reported live smoke call succeeded using OpenAI SDK 2.30.0: the response model was `zai-org/GLM-5.3`, the fixed response was `FuturePath API OK`, and reported usage was 20 prompt / 6 completion tokens. This verifies one simple request only; it does not verify the application-pinned OpenAI SDK 2.11.0 against the live endpoint, any of the four integrated workflows, shared Redis enforcement, provider billing, live pricing, or production readiness. Official RunPod documentation describes the generic OpenAI-compatible Chat Completions path for serverless vLLM endpoints, but does not identify this exact competition endpoint/model pair: https://docs.runpod.io/serverless/vllm/openai-compatibility. The adapter uses non-streaming Chat Completions, a 20-second SDK timeout, disabled SDK retries, and at most one compatibility retry after an explicit unsupported-`reasoning_effort` 400 response.

Redis URL query options and fragments are not accepted. Use the credentials/hostname/port/database URL form. The client explicitly requires certificate validation and hostname matching. Do not bypass those checks to make configuration work.

Redis atomically reserves estimated cost and checks requests, sessions, and concurrency before calls. Missing usage and failed calls retain a conservative reservation charge. This is an estimated application guard, not a provider-enforced dollar cap. Daily limits use UTC. Browser renewal can create a new session; shared request and cost limits remain necessary. The 90-second concurrency lease must exceed the verified provider request duration. All replicas must share the same Redis service and consistent configuration. Unavailable accounting blocks AI output. Real Redis Lua integration is still unverified.

## Privacy, safety, and external gates

The user separately consents before transmitting a bounded question and minimal synthetic context. Recent chat and profile edits stay in the active Streamlit session. Application usage logs contain request ID, feature, model, token counts, estimated cost, and status only. The provider filters SDK and HTTP transport loggers so debug configuration cannot emit request payloads through the pinned transport logging paths. Unknown skills are not confirmed gaps, and AI cannot change deterministic scores or approval status. Malformed or unsupported AI results fall back to the deterministic application.

Generated prose rejects external hyperlinks. Suggested chat follow-ups remain in the current session and do not trigger requests automatically. Schema and reference checks reduce unsupported output but cannot establish its factual truth.

Before public AI activation, verify the application-pinned SDK with an explicitly authorized small live request, actual usage and reasoning accounting, current prices, provider account spending controls, and a real shared Redis service. Keep public AI disabled until these pass. A single reported endpoint smoke is recorded but does not satisfy these gates. Before publication, also verify the Replit Build/Run logs, anonymous HTTPS journey, WebSocket connectivity, session isolation, redacted application logs, and exact deployed source/package provenance. No public deployment or public AI availability is claimed by this candidate.

Licensing: see `LICENSE` and the English maintained derivative `THIRD_PARTY_NOTICES.en.md`; the original legal and historical records remain preserved in the development repository.

The complete 55-pin inventory is `RUNTIME_DEPENDENCIES.csv`. `THIRD_PARTY_RUNTIME_NOTICES.zip` retains 90 captured license/attribution files and their hashes. These cover inspected Windows distributions; upstream Streamlit license text was captured separately with normalization noted in the inventory. Bundled-component terms remain applicable. Linux wheels, frontend assets and model/platform service terms require their own review. This companion is not a blanket legal-compliance certification.
