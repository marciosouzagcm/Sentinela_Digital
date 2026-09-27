# Official Submission Brief — Sentinela Digital

*Crypto World's Fair Hackathon — Colosseum Org LLC. Prepared 2026-09-27. This is a working submission brief, not a certification that an entry has been submitted or is eligible.*

> **Evidence standard.** Product and repository statements below are based on the checked-out source tree and Git history available on 2026-09-27. Personal biography, contact details, intent to submit, interview availability, number of entries and legal eligibility are participant-provided and must be confirmed by the team leader in the Colosseum portal. Do not mark an unverified item complete or claim revenue, customers, uptime, deployment or 100% in-window authorship without evidence.

## 1. Basic Information & Schedule

- **Project:** Sentinela Digital
- **Team Leader / Official Contact:** Márcio Souza — `marciosouzagcm@gmail.com` *(provided by team; confirm this exact address in the Colosseum account before submission)*
- **Team Members:** Márcio Souza — Full-Stack & Security Engineer *(provided by team; confirm all member names and required account registrations)*
- **Hackathon:** Crypto World's Fair, Colosseum Org LLC.
- **Contest Period:** September 14, 2026 through October 12, 2026. The campaign page confirms “SEP 14 — OCT 12” and says submissions are due October 12, 2026. The supplied rules summary gives 06:00 AM PT as the start and 11:59 PM PT as the deadline; verify these exact times and the applicable official-rules version in the submission portal before relying on them.
- **Deadline in Brasília time (BRT, UTC−03:00):** October 13, 2026, 03:59 AM BRT, if the official cutoff is October 12, 2026, 11:59 PM Pacific Daylight Time (UTC−07:00). Submit earlier and use the portal countdown as authoritative.
- **Winners:** The date “by December 5, 2026” is in the team-provided draft; it was not independently confirmed from the campaign page during this update. Check the portal/official rules for the announcement date.
- **Primary Track:** Solana Ecosystem. The official campaign page lists a $100,000 Solana track pool with 10 projects receiving $10,000 each; track awards are additional to overall campaign awards.
- **Interview availability:** Márcio reports availability for a 15-minute Zoom interview during the month after the deadline *(team-provided; reconfirm before submission)*.

**Official references checked on 2026-09-27:**

- Campaign overview, schedule, awards, track and accelerator information: [Crypto World's Fair](https://colosseum.com/worldsfair).
- Official rules PDF linked from the campaign page: [Crypto World's Fair Hackathon Rules](https://colosseum.com/legal/Crypto%20World's%20Fair%20Hackathon%20Rules.pdf). The PDF could not be text-extracted in this review; the rules and portal must be checked directly for all legal requirements, exact timestamps and eligibility.
- The current official page describes the event as an open competition across crypto ecosystems and lists the track award separately from overall awards. Do not interpret this brief as legal advice.

## 2. Eligibility & Official Rules Compliance Checklist

Use checkboxes only after the leader has verified each item in the portal and the official rules. Current status is deliberately **not certified** where repository evidence cannot establish it.

- [ ] **One submission per team/person:** Confirm the team has not submitted another project and that the portal shows this project as the team's sole entry.
- [ ] **Leader submits on time:** Submission receipt and timestamp have not been provided. Submit before the portal's October 12 cutoff and retain the receipt.
- [ ] **Work during the contest period / pre-existing work disclosed:** **Pre-existing work exists.** Git history contains Sentinela commits dated September 7–10, 2026, before the campaign's September 14 start. The tree also contains substantial pre-existing OSINT, scanner, report and PDF code. Identify the prior baseline in the submission and distinguish it from material work completed September 14 onward. Do not state “100% developed during the window.”
- [ ] **Team authorship / third-party assistance disclosed:** Git log entries during the window use the author name Marcio Souza, but show the placeholder email `seu.email@exemplo.com`; Git metadata alone does not prove the identity of every contributor or the origin of each change. The team reports strategic use of AI tools; disclose AI assistance and external contributions according to the official rules and submission form. Keep dependencies, frameworks, wallet adapters and other reused libraries distinct from the team's own product work.
- [ ] **Intellectual property:** The entrant's retained-IP claim must be checked against the official rules, any third-party assets/licenses, team agreements and portal attestations. Do not certify ownership beyond the rights actually held.
- [ ] **Content / conduct / security:** Review campaign rules and code of conduct directly. Product positioning is defensive security for explicitly authorized targets; demos and scans should use authorized assets and avoid real credentials or private RPC secrets.
- [ ] **English-language submission materials:** Prepare the portal description, pitch and demo narration in English if required by the campaign/submission instructions. This internal working brief is in English for reuse in the application.

### Repository evidence for work in the window

The checked-out history as of September 27 shows the following entries. The commit subjects are summaries, not independent proof of authorship, functionality, deployment or eligibility.

| Commit | Date | Recorded subject |
| --- | --- | --- |
| `edc5fb5` | Sep 14, 2026 | Project refactor |
| `2df5a1d` | Sep 18, 2026 | Consolidate web/OSINT report pipeline |
| `424a043` | Sep 18, 2026 | PDF action plan and empty findings handling |
| `17bf2df` | Sep 19, 2026 | GHunt cookie model and resolution improvements |
| `6c74e26` | Sep 22, 2026 | OSINT adapter refactor, tests and target-specific PDF |
| `44df6b9` | Sep 22, 2026 | Report/PDF generation documentation and cleanup |
| `14f30de` | Sep 22, 2026 | Blockchain module and PDF posture updates |
| `c07ea07` | Sep 23, 2026 | Hackathon implementation/architecture status |
| `404eebf` | Sep 26, 2026 | Checkout polling and Error Boundary fixes |

Each visible commit is recorded as “Marcio Souza” with the placeholder email `seu.email@exemplo.com`. Correct or explain the Git identity in the submission evidence and preserve original history. Earlier commits dated September 7–10 are pre-contest baseline; disclose the existing OSINT, scanner, report and PDF code rather than claiming the complete product was created during the contest window.

## 3. The Seven Judging Factors

### 1. Founder + Market Fit

- **Founder profile:** The team-provided biography says Márcio is an Analysis and Systems Development student at FACINT, participates in Hackers do Bem, and works across Python automation, Solana/Web3 and cybersecurity. Confirm education, participation and experience details before publishing them as verified credentials.
- **Founder insight and motivation:** The founder wants to make authorized, focused security checks accessible to smaller organizations and Web3 teams through a low-friction, metered workflow. Support the claim with user interviews or pilot evidence when available.

### 2. Insight

Security reviews are often packaged as enterprise engagements or subscriptions, while operators sometimes need a narrow, repeatable check. Sentinela's product hypothesis is that a single-query purchase and a unified result can lower the commitment required for an authorized check. Solana Pay is used for payment settlement and an auditable order reference; it is not presented as a security oracle or as proof that an asset is safe.

### 3. Product + Execution

- **Product implemented in the repository:** React/Vite checkout and dashboard; FastAPI order and payment-verification routes; SIWS-style nonce challenge with Ed25519 verification and JWT issuance; Solana RPC service for SOL balance, SPL/Token-2022 holdings, `.sol` resolution and configurable local flags; OSINT/scanner adapters including Nmap-based network checks; SQLAlchemy/TiDB Cloud data models; JSON/PDF reporting via ReportLab.
- **Payment validation:** The server persists order details and checks a confirmed transaction against the order's reference, signer, treasury recipient and expected lamports before adding credits. Verification is cluster-configurable (`mainnet-beta` / `devnet`); demo mode, when enabled, is presentation-only and does not credit the backend.
- **Execution evidence:** The repository contains unit tests for SIWS, payment checks, Solana service and reporting. Cite current test output, an actual deployment URL, a reproducible demo and a real authorized end-to-end payment only after each has been run and recorded. Do not describe this as “fully operational” solely from source code.
- **Payment-to-pipeline resilience:** Confirmed payments are persisted in the TiDB Cloud `payments` table with the Solana signature, reference, target and lifecycle status (`PENDING`, `CONFIRMED`, `SCAN_IN_PROGRESS`, `COMPLETED` or `FAILED`). The post-payment worker opens its own database session, prevents duplicate scheduling and records the PDF path or the exact scan/PDF error. In Linux deployments, grant Nmap raw-socket access with `sudo setcap cap_net_raw+eip $(command -v nmap)` when the host policy permits it; otherwise the permission failure is recorded as a failed payment pipeline instead of being silently lost.
- **Competitive positioning:** Describe the alternative workflows the team has actually compared (manual tools, hosted scanners, security consultancies). Avoid claiming a unique or uncrowded market without documented comparison research.
- **Delivery speed:** The in-window Git history records incremental work from September 14–26, including scanner/report pipeline changes, blockchain intelligence and checkout resilience. The project also has commits dated before the event; present the sequence transparently as baseline plus hackathon-period iterations.

### 4. Potential Market Size

The target users are small and midsize organizations, independent developers, and Web3 teams needing authorized, bounded checks of web infrastructure, identity exposure or public wallet data. Cybersecurity and OSINT are broad categories, but this brief does not have a sourced TAM/SAM/SOM calculation. Build one from cited market research and a bottom-up reachable-customer model; do not substitute a global industry headline for the market the product can actually serve.

### 5. Founder Communication

- **One-line vision:** “Make authorized security checks easier to buy and act on by combining familiar security tooling with transparent, per-query settlement on Solana.”
- **Pitch narrative:** Pain → target user → why existing options do not fit the narrow use case → live authorized demo → payment and report evidence → business model → limitations and next milestones.
- **Presentation evidence:** Prepare an English written submission and a concise demo video within the campaign's applicable requirements. A 15-minute Zoom interview is the team's stated availability, not a verified requirement unless the official rules say so.

### 6. Viability

- **Initial business hypothesis:** Pay per completed report/scan, with optional bundles or team plans only after customer validation.
- **Cost and margin still to measure:** RPC usage, scanner execution time, third-party API fees, report generation, database/storage, abuse prevention, support, and any limits imposed by target authorization or data-provider terms.
- **Next validation:** Interview target users, test willingness to pay, measure per-query cost and completion rate, define refund/failure behavior, and establish safe-use, retention and privacy policies. “Low cost,” “high margin,” and “scalable” remain hypotheses until measured.

### 7. Traction

- **Evidence available in the repository:** A functioning application codebase, Git history across the event window, integration tests, and implementation of checkout, wallet authentication, scanner adapters and reports.
- **Evidence not provided in this brief:** External users, paid transactions, repeat usage, revenue, signed pilots, or production uptime. Do not claim those forms of traction unless the team can attach dated records and obtain permission to share them.
- **Evidence to collect:** Number of authorized demos, successful end-to-end payments by cluster, completed reports, time to report, user interviews, repeat use and conversion. Clearly separate testnet/demo events from real customer activity.

## 4. Repository Review & Authorship Disclosure

- **What the repository review is intended to show:** Meaningful, strategically prioritized work during the contest period; work attributable to the team; and a product progression that is legible in the history. Code language, framework choice and code-style polish are not substitutes for this evidence.
- **Pre-contest baseline:** The Git log shows commits from September 7, 9 and 10 before the official campaign start shown as September 14. These include existing OSINT adapters, scanners and PDF/report work. Disclose these as the pre-existing foundation rather than claiming the whole project was created in the contest window.
- **In-window work visible as of September 27:** Commit history records activity from September 14 onward, including September 18–22 OSINT/report and blockchain work, September 23 project documentation, and September 26 checkout/polling fixes. Keep original commit hashes, dates and author records; correct placeholder Git identity metadata where appropriate without rewriting history in a misleading way.
- **Team authorship:** Current visible commit author names are “Marcio Souza” while the email is `seu.email@exemplo.com`. Confirm identity and contributor attribution; disclose use of AI coding tools and third-party libraries according to official rules. Do not claim “100% human-written” or “100% built during the window.”
- **Strategic prioritization:** Explain why the team chose the payment/order flow, on-chain verification, SIWS, authorized scanning and actionable reporting as the core demo, and disclose what is still experimental or incomplete.
- **Repository review technical note:** Identificado e corrigido o desacoplamento entre a confirmação on-chain Solana Pay e o disparo do worker assíncrono. Como a transação ocorre com sucesso na blockchain, a arquitetura foi reforçada com tabelas de controle no TiDB Cloud, tratamento de exceções de privilégios do Nmap no Linux e polling persistente no backend FastAPI.

## 5. The Four Questions a Judge Must Answer

### A) Is the problem real? *(Insight, Potential Market Size, Viability)*

**Working answer:** There is a plausible need for smaller, bounded, authorized security checks without committing to an enterprise engagement. The current evidence supports a product hypothesis, not yet proven demand or a verified market size. Show interview notes, competitor alternatives, a bottom-up customer model and willingness-to-pay tests; do not imply proven savings or margins without measurements.

### B) Does the product work? *(Product + Execution)*

**Working answer:** The repository implements an end-to-end path in which a user creates an order, the backend verifies a transaction on the configured Solana cluster, and accepted payment can add credits and schedule a scan/report. Demonstrate the complete path live in the same cluster and environment used by the wallet. If using demo mode, label it as UI-only: it does not confirm chain state or add backend credits. Show test results and partial-failure handling; disclose RPC/DB/adapter limitations.

### C) Is the story convincing? *(Founder Communication)*

**Working answer:** Position Sentinela as a security workflow with metered Solana settlement, not “security because blockchain.” Explain who needs a query, what evidence the report returns, why per-query payment fits, and what is not yet proven. Deliver the explanation and demo in clear English if required by the submission form.

### D) Can this team execute? *(Founder + Market Fit, Repository Review, Interview)*

**Working answer:** The repository contains a pre-existing foundation and dated iterations during the contest window. A credible account must separate the two, identify the actual contributors and AI/library assistance, and connect each in-window change to a product priority. The founder's background and interview availability are team-provided and should be confirmed before the submission makes them factual claims.

## Submission-Day Verification Checklist

- [ ] Read and retain the linked official rules PDF and any portal amendments; confirm exact cutoff/time zone and eligibility.
- [ ] Confirm team leader, members, account registrations, one-submission limit and submitter permissions.
- [ ] Review and truthfully disclose pre-existing code, team contributions, AI assistance, third-party libraries, assets and licenses.
- [ ] Verify every checkbox and factual claim in the submission portal; do not present this draft as evidence of an already-submitted project.
- [ ] Run a fresh end-to-end demo with an authorized target and the correct Solana cluster; label testnet and UI-only demo behavior accurately.
- [ ] Attach only evidence the team owns or may share (video, test logs, user feedback, payment/report examples); remove secrets and personal data.
- [ ] Save the portal submission receipt and the final rules/brief versions used.
