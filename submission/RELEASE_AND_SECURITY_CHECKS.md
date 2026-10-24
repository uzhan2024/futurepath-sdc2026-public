# Submission Documentation Release Checks

Recorded 25 October 2026 MYT. This record covers a documentation/POU-only branch update. It is not application deployment or final competition acceptance.

## Immutable application release

- Approved source: `20fefb588189712de1132d91e0560a9841a46c21`.
- All 42 release members are byte-identical to the approved commit and ZIP.
- Original Manifest SHA-256: `5c8356bd365a14361b0c3ab976d4eb788c28b15bad795db704d5a3b5a312136b`.
- Original ZIP SHA-256: `8681173dacdd4a8beb5d3ddfb38396a414d7da03fa877460bc64e2632dc071d0`.
- Independent 42-file export: original `verify-root` PASS.
- Expanded documentation roots intentionally fail the original exact-membership verifier. Its policy and Manifest were not changed.
- Runtime pins/inventory: 55/55 exact name/version matches; 90/90 retained attribution sizes and SHA-256 values pass.
- Application code, matching, fixtures, deployment settings, AI/CV defaults, main and default-branch settings are unchanged.
- No new runtime/full-suite run is claimed. Historical approved RC2 evidence remains 491 passed and 1 intentionally skipped paid-live test.

## Corrected unsigned forms

The official section order, tables, page geometry and source package parts outside `word/document.xml` were retained. New content extends some tables across repeated-header continuation pages. The source DOCX and original signed PDFs are unchanged.

Both revised DOCX files were rendered with the packaged document renderer and existing isolated portable Windows LibreOffice. All 22 final pages were visually reviewed, including signatures, checklists and table continuations. The new files have no transferred signature, no signing date, and no unresolved old VERIFY/SOURCE CHECK/FINAL REVIEW markers. Explicit human-review statements are intentional.

| Form section | Words | Limit |
|---|---:|---:|
| Preliminary 2.1 | 108 | 250 |
| Preliminary 2.2 | 157 | 300 |
| Preliminary 3.2 | 91 | 200 |
| TechDeclaration 2.1 | 133 | 200 |
| TechDeclaration 4.3 | 62 | 100 |
| TechDeclaration 5 | 59 | 100 |
| TechDeclaration 6.1 | 95 | 150 |
| TechDeclaration 6.2 | 71 | 150 |

The Proposal problem-context mapping is supported by the official DOSM Q2 2026 overall rate of 35.2%; this is national context, not a measured product outcome. The contextual statistic was checked directly against the official CSV; no product impact measurement is inferred.

Technical checklist items for sponsor-resource disclosure and anonymous link availability are checked from the recorded evidence. Five final completeness/rights/privacy/AI-review assertions remain for the leader; no unsupported legal box was ticked. Proposal final completeness and the employment/IP confirmation also require leader review. Both forms need fresh signatures/dates and are deliberately excluded from this public commit.

## Public proof of use

| File | SHA-256 |
|---|---|
| [`Replit`](proof-of-use/SDC2026_FoolsHorizon_Replit_POU.pdf) | `3699d648e0b6a767424c83a513cb73ace5d5d7a223eb70eba3a73dbe674a74ba` |
| [`OpenAI_Codex`](proof-of-use/SDC2026_FoolsHorizon_OpenAI_Codex_POU.pdf) | `4d08b94313d914d49dd8211d1d07bb4bd4c7c37b6cabe762fccc7f6a265fdd26` |

Both PDFs match the supplied archive exactly and their eight pages were visually inspected. No visible keys/passwords/tokens were observed. Text/decoded-stream credential-pattern checks and active-action/embedded-file checks returned no findings in the audited files. This is bounded inspection, not provider account authentication or a malware/legal certification.

Replit costs are account-wide across all workspaces. Codex charts exclude ordinary Chat conversations. Neither proves project-specific spend, sponsored credits or RunPod use. RunPod's separately reported successful connectivity test is disclosed; independent account POU and exact sponsored accounting are not supplied.

## Links, privacy and source boundaries

Anonymous read-only checks returned 200 for the new live app, 200 / `ok` for health, and 200 for the video page/oEmbed metadata. Full playback/duration, deployed commit, WebSockets and production logs are not established by these checks.

Only project documentation, this report and two reviewed POU PDFs belong to this update. No incomplete/unsigned form, private resume, raw prompt, account credential, local environment, cache, model weight or internal engineering log is staged. Public disclosure was authorised by the owner, but that does not replace final leader signatures.

Staged-path, relative-link, new-text/decoded-PDF and reachable-history credential-pattern checks passed. The original 42 staged blobs and protected refs match their recorded values. Markdown whitespace checks passed; PDFs retain their original format whitespace and are validated byte-for-byte against the source bundle rather than rewritten as text. Push only `submission/sdc2026-final` without force. No competition upload or app deployment is part of that push.

## Primary references

- [DOSM dataset definition](https://data.gov.my/data-catalogue/lfs_qtr_sru_sex) and [official CSV](https://storage.dosm.gov.my/labour/lfs_qtr_sru_sex.csv).
- [O*NET 31.0 licence and exceptions](https://www.onetcenter.org/license_db.html).
- [OpenAlex metadata scope](https://help.openalex.org/data/how-its-built/).
- [Qwen3.5-4B upstream model card](https://huggingface.co/Qwen/Qwen3.5-4B). Installed local metadata also returned Apache-2.0 without running inference.
- Existing repository notices/inventory remain authoritative for the pinned runtime; service/model rights are separate.
