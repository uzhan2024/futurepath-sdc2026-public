# FuturePath Intelligence

**Fool's Horizon | SDC Hackathon 2026 | Domain 1 - Aiversecity Future-Ready Workforce**

FuturePath is an English-language career exploration prototype for learners and early-career users. It turns explicitly reported skills into transparent career comparisons, confirmed skill gaps and practical learning steps. The selected competition track is SDG 4 - Quality Education; no measured educational or employment impact is claimed.

**Synthetic Demo:** all shipped occupation requirements and sample profiles are fictional demonstration data. Results are not verified labour-market findings, professional career advice, qualifications or predictions of employment.

## Start here

- [Watch the demo video](https://youtu.be/Pzd7-IM2w-8)
- [Open the owner-provided V3 RC2 application](https://futurepath-sdc-2026-public-1.replit.app/)
- [Existing public prototype](https://futurepath-sdc-2026-public.replit.app)
- [Architecture and trust boundaries](docs/architecture.md)
- [Submission documents and outstanding approvals](submission/README.md)
- [Immutable release contract](PUBLIC_RELEASE.md)
- [Runtime dependency inventory](RUNTIME_DEPENDENCIES.csv)
- [Third-party notices](THIRD_PARTY_NOTICES.en.md)

Anonymous HTTP checks on 25 October 2026 MYT returned 200 for the public prototype and 200 / `ok` for its health endpoint. This is availability evidence only. The deployed commit, V3 feature availability, independent V3 Staging, WebSocket behaviour and production logs were not verified in this documentation task. The existing public deployment remains the fallback. No new deployment or public AI/CV activation is claimed.

**New submission links: PROVIDED.** The owner supplied the demo video and V3 RC2 application URLs above. Independent anonymous accessibility, video playback/duration and application deployment/version verification are pending; these links are not marked independently verified. The earlier availability checks above concern the existing fallback URL only.

## Problem and solution

A list of career recommendations can hide missing information and make uncertain matches look precise. FuturePath makes the user's reported knowledge visible, separates confirmed gaps from unanswered questions, and connects the resulting comparison to editable learning preferences and team-authored practice exercises.

The prototype supports a complete manual journey without an AI provider, cloud credentials or Redis: open the dashboard, choose or create a profile, report skills, examine matches, compare careers, choose a learning path and revise inputs.

## Capabilities and verification boundaries

| Capability | Approved V3 RC2 source | Public availability |
|---|---|---|
| Manual profile and four-state skill intake | Implemented; deterministic and UI tests | Existing prototype supports the core journey; deployed version not established here |
| Career matching and explanations | Implemented; deterministic scoring remains authoritative | Existing core prototype |
| Confirmed skill gaps and career comparison | Implemented with synthetic requirements | Existing core prototype |
| Learning roadmap and practice progress | Implemented; user-entered preferences, no assumed budget | Exact production version not established here |
| AI Career Advisor, Skill Gap Coach, Learning Roadmap and contextual Chat | Implemented through a shared provider contract; mocked regression coverage and prior real local Ollama component tests | Disabled by the approved Replit configuration |
| PDF/DOCX resume-to-profile | Implemented locally; partially validated, with confirmation before matching | Disabled by the approved Replit configuration; no public CV availability claimed |
| RunPod GLM-5.3 adapter | Implemented and mock-tested; one separate owner-reported endpoint smoke succeeded | Integrated application and production cloud use remain unverified |

The maintained V3 UI is English and removes schema versions, internal profile codes and build/debug metadata from the normal user journey. Responsive Streamlit controls and horizontally scrollable task tabs are used; this is not a claim of a comprehensive device/accessibility audit.

## Matching methodology

Each required skill has one of four states:

| State | Meaning |
|---|---|
| Known Present | The user explicitly confirms the skill |
| Known Absent | The user explicitly reports a gap |
| Unknown | The user cannot yet establish the state |
| Not Reported | No assertion has been supplied |

For a role with `W` requirements and `P` confirmed-present skills, complete synthetic skill coverage is `100 * P / W`. It is displayed and ranked only when every requirement is Known Present or Known Absent and `W > 0`. Unknown and Not Reported remain separate and suppress complete scoring/ranking. They are never silently converted into absence.

Information coverage and uncertainty bounds support explanation of incomplete profiles. The result is a transparent count-based synthetic comparison, not a probability of career success. Completing a practice checklist does not establish proficiency or increase a score. AI output never changes scores, ordering, user confirmations or data approval.

## Architecture

The application is a Python + Streamlit modular monolith. Session state holds the active profile, learning settings, practice choices and bounded chat.

| Path | Responsibility |
|---|---|
| `app.py`, `ui/` | Nine task tabs, input confirmation, result presentation and optional AI controls |
| `domain/` | Typed profiles, skill states and matching contracts |
| `fixtures/` | Integrity-checked synthetic profiles and fictional role requirements |
| `services/matching.py` | Deterministic assessment and ranking gates |
| `services/ai_guidance.py` | Grounded advice, gap coaching, roadmap and bounded chat |
| `services/llm/` | Provider contract, Ollama and RunPod adapters, mock and output schemas |
| `services/resume_parsing.py`, `services/resume_profile.py` | Bounded parsing, local extraction, evidence validation and user confirmation |
| `services/ai_budget.py` | Shared cloud usage reservations and fail-closed accounting |
| `deployment/public_package.py` | Exact release allow-list, hashes and root verification |

See [architecture](docs/architecture.md) for the trust boundaries and data flow.

## AI, tools and actual usage

Local development prefers Ollama at a literal loopback endpoint. The adapter discovers installed models, requests bounded structured JSON, validates output and fails safely when unavailable. Models are never downloaded automatically. Prior release evidence records real local `qwen3.5:4b` component tests and a short fictional resume extraction. A longer fictional resume case failed strict validation; CV reliability remains partial. No new model call or benchmark was run for this documentation change.

The provider layer supports `ollama`, `runpod`, `disabled` and explicitly injected test mocks. AI is optional, requires session consent and supplies explanations rather than authoritative labour-market facts. No web research or live workforce forecasting is implemented.

One owner-reported manual RunPod request used request model `glm-5.3` and returned model `zai-org/GLM-5.3`, text `FuturePath API OK`, 20 prompt tokens and 6 completion tokens. That smoke used OpenAI SDK 2.30.0; this release pins 2.11.0. It does not verify the four integrated workflows, the pinned SDK against the endpoint, shared Redis, billed credit consumption or production readiness. No paid API request was made in this preparation task.

RunPod defaults are conservative: 512 output tokens, 8,000 input bytes, a 20-second SDK timeout, no SDK retries and at most one explicitly bounded unsupported-parameter compatibility retry. Cloud requests require a server-only key and a reachable shared TLS Redis guard. Default estimated limits are USD 0.10 per UTC day, 10 requests per day, 3 per session per day and concurrency 1. All replicas must share the guard. These are application estimates, not provider-enforced billing caps; pricing, reasoning accounting and real shared enforcement remain separate validation gates.

Codex, ChatGPT and Replit Agent were used as development assistants. Replit is the existing hosting service. Ollama was used locally; a RunPod adapter and the reported endpoint smoke are disclosed separately. Tool/service/model terms are distinct from the Python dependency licenses. Sponsor eligibility, credited amount and actual billed consumption still require owner evidence.

## Privacy and resume limitations

Resume import is optional and local-only in the approved design. It accepts bounded PDF/DOCX text, validates document structure and parses in a child process with time/memory limits. Limits include 2 MB uploads, 10 PDF pages and 12,000 extracted UTF-8 bytes; scanned, encrypted or unsupported complex documents may be rejected.

Retained extracted claims must be supported by source text. A skill mention is only a suggestion; the user must review and explicitly confirm skill states before matching. Background claims do not enter scoring. Raw resumes, prompts and generated advice are not intentionally persisted or logged by application code. There is no silent cloud-CV fallback.

Session clearing is not a secure-erasure guarantee for framework buffers, model memory, host logs or swap. Before using any private resume locally, confirm the Ollama daemon itself listens only on loopback: the prior host audit found an existing wildcard listener. A loopback client URL alone does not secure that service. Fictional documents were used in tests. Public CV upload and public AI stay disabled.

## Reproducible Python 3.12 setup

**This submission branch adds documentation; it is not the strict deployment root.** The approved release has exactly 42 files, including its original Manifest. The verifier intentionally rejects extra submission documentation. Do not regenerate the original Manifest, relax its allow-list or deploy this expanded root.

Use a new directory containing the approved release branch/commit for runtime verification. The following commands do not modify an existing checkout.

Windows CMD:

```bat
git clone --branch candidate/v3-rc2-20261025 https://github.com/uzhan2024/futurepath-sdc2026-public.git FuturePath-RC2-clean
cd FuturePath-RC2-clean
git checkout --detach 20fefb588189712de1132d91e0560a9841a46c21
py -3.12 -B deployment\public_package.py verify-root
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --no-user -r requirements-public.lock
.venv\Scripts\python.exe -m pip check
set FUTUREPATH_DEPLOYMENT_MODE=local
set FUTUREPATH_AI_PROVIDER=disabled
set FUTUREPATH_CV_ENABLED=false
.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
```

Open `http://127.0.0.1:8501`. Deterministic features work with AI disabled and without a resume. Optional local Ollama requires an already installed model, a loopback-only daemon and consent; see the [release contract](PUBLIC_RELEASE.md). Do not enable cloud AI merely to complete the demonstration.

Linux uses `python3.12` and `.venv/bin/python` in place of the Windows interpreter paths. This is the intended configuration, not evidence that a new Linux/Replit Publishing Build has passed.

## Replit deployment boundary

The unchanged `.replit` uses `.venv/bin/python` for both development Run commands and deployment Run. It forces public mode, AI disabled and CV disabled. Build verifies the original clean root, creates the virtual environment and installs `requirements-public.lock` with `--no-user`. Root `requirements.txt` and Agent memory files are excluded.

The historical pre-Build automatic `pip install -r requirements.txt` failure remains a platform verification concern. Removing that root filename is a reviewed mitigation, not documentation-backed proof that every automatic installer is suppressed. A new Publishing claim requires actual Build/Run logs and anonymous acceptance tests. This submission task neither changes Replit nor authorizes publication.

## Tests and release provenance

Approved source commit: [20fefb588189712de1132d91e0560a9841a46c21](https://github.com/uzhan2024/futurepath-sdc2026-public/commit/20fefb588189712de1132d91e0560a9841a46c21).

| Evidence | Recorded result |
|---|---|
| Approved RC2 full development suite | 491 passed, 1 intentionally skipped live test; 68.25 seconds |
| Reviewed release members | 41 source files plus the original Manifest; 42 total |
| Submission-preparation runtime smoke | Python 3.12.2; 55 installed pins, pip check, manual journey, incomplete-score gate, session isolation, fictional DOCX and HTTP health passed |
| Runtime dependencies | 55 exact pins: 7 direct and 48 transitive |
| Retained license/attribution captures | 90 items, with recorded hashes |
| Approved ZIP SHA-256 | `8681173dacdd4a8beb5d3ddfb38396a414d7da03fa877460bc64e2632dc071d0` |
| Original Manifest SHA-256 | `5c8356bd365a14361b0c3ab976d4eb788c28b15bad795db704d5a3b5a312136b` |

The full suite is development evidence; test sources and private engineering reports are deliberately absent from the sanitized runtime package. This documentation task does not claim another full-suite run. The submission branch must retain all 42 approved files byte-for-byte; verification uses a separate clean exported release tree. Documentation checks and runtime smoke results are reported separately from inherited suite evidence.

The attribution archive deliberately retains its historical 53-entry inventory files; the current top-level `RUNTIME_DEPENDENCIES.csv` is the authoritative 55-entry release inventory. All 90 attribution members were rechecked against their recorded sizes and SHA-256 values during this submission preparation.

The source Manifest does not hash installed wheels. The 55-pin lock does not contain wheel artifact hashes. The 90 retained captures cover inspected Windows distributions; Linux wheels, frontend components and model/platform terms require their own review. No blanket security or legal certification is claimed.

## License and submission

Project source: [Apache License 2.0](LICENSE). Preserve the [third-party notices](THIRD_PARTY_NOTICES.en.md), [runtime inventory](RUNTIME_DEPENDENCIES.csv) and [captured attribution archive](THIRD_PARTY_RUNTIME_NOTICES.zip).

Official-form review copies exist privately, but contain personal information and unresolved declarations/signatures. They are not published here. See the [submission inventory and human checklist](submission/README.md). No signature, proof-of-use PDF, final video, competition upload or submission is fabricated.

Known limitations include synthetic-only roles, no live job/salary data, partial local CV validation, unverified integrated cloud AI, unverified new Linux Publishing and no measured career outcomes. Preserve the current production fallback until a separately authorized replacement passes real platform gates.
