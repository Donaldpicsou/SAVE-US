# SAVE-US — Hackathon Submission Priorities

This checklist prioritises the work that most improves SAVE-US’s OpenAI Build Week submission. It is based on the official requirements and the current MVP state.

## Submission positioning

- **Recommended track:** Apps for Your Life.
- **Core promise:** SAVE-US helps Central African communities structure, review, safely distribute, and share critical emergency alerts.
- **Differentiator:** GPT-5.6 acts as a first-line investigation assistant: it structures reports, identifies missing or inconsistent information, detects possible duplicates, evaluates confidence and fraud risk, and applies country/region targeting rules.
- **Safety statement:** SAVE-US does not verify facts, contact authorities, or replace emergency services. It protects private contacts, exact addresses, coordinates, and original uploaded media.

## Priority 0 — Required before submission

### 1. Create a complete README and add a license

Create `README.md` before publishing the final submission. It must include:

- Project purpose and the CEMAC problem addressed.
- Main working features and known MVP limits.
- Installation instructions: Python environment, dependencies, database migration, demo data, and local launch command.
- Demo access instructions, including the simulated OTP flow and the demo OTP code `123456`.
- Test command: `.venv/bin/python -m unittest discover -s tests -q`.
- Architecture summary: Flask, SQLite, SQLAlchemy, private media storage, OpenAI Responses API, deterministic fallback.
- Security and privacy choices: protected media, no public private contacts, approximate public location only, targeted alerts, and audit trail.
- A **“Built with Codex and GPT-5.6”** section explaining:
  - where Codex accelerated implementation, testing, visual integration, and documentation;
  - which product, engineering, and safety decisions were made deliberately by the team;
  - how GPT-5.6 is used for structured server-side review and accident-media moderation;
  - how the deterministic fallback keeps the demo runnable without an API key.
- A clear distinction between work created or meaningfully extended during the hackathon and any earlier work.

Add an appropriate open-source license to the public repository.

### 2. Provide a working demo for judges

- Deploy SAVE-US to a stable public URL, or provide a fully reproducible test build.
- Ensure database migration and demo seeding work on the deployment.
- Provide a documented test account, phone number, and OTP code.
- Confirm the application works without manual database intervention.
- Keep the demo free and available for the full judging period.

### 3. Record the Devpost demonstration video

- Publish it on YouTube and make it publicly visible.
- Keep the video below **three minutes**.
- Include clear audio.
- Show both what was built and how Codex and GPT-5.6 were used.
- Do not use unlicensed music, third-party marks, or personal data.

Suggested 2:50 video structure:

1. **0:00–0:20 — Problem and promise**
   Explain the Central African emergency-information gap and the safety-first SAVE-US approach.
2. **0:20–1:05 — Missing-person report**
   Show Cameroon/Centre onboarding, a structured report, and protected photo upload.
3. **1:05–1:35 — GPT-5.6 review**
   Show the structured review: safe summary, extracted data, missing fields, duplicate signal, confidence, and fraud risk. Make clear that this is a server-side GPT-5.6/OpenAI Responses API review.
4. **1:35–2:00 — Targeting and moderation**
   Show an eligible recipient’s notification/feed and a moderator decision with audit reason.
5. **2:00–2:20 — Shareable alert sheet**
   Demonstrate the printable/PDF sheet and safe WhatsApp sharing with `Source: SAVE-US` once implemented.
6. **2:20–2:40 — Multi-event rules**
   Contrast a country-wide suspected abduction with a regional road accident and its expiry.
7. **2:40–2:50 — Codex contribution and impact**
   State how Codex accelerated the MVP and why the approach can scale responsibly across CEMAC.

## Priority 1 — Complete the key unfinished PRD promise

### 4. Deliver alert sheet, PDF, and sharing (Roadmap T49–T54)

The current alert-detail buttons are not functional. Complete the sharing branch in this order:

- **T49:** Define a single English public-safe alert-sheet contract.
- **T50:** Build a branded A4 printable HTML sheet.
- **T51:** Generate a server-side PDF from the same safe content.
- **T52:** Create opaque, revocable, expiring secure share links.
- **T53:** Add copy-link, Web Share fallback, and prefilled WhatsApp sharing with `Source: SAVE-US`.
- **T54:** Test printing, PDF output, English text, attribution, revoked links, and exclusion of private data.

The sheet and external share link must never expose:

- private family or reporter contact details;
- exact street address or GPS coordinates;
- private circumstances or internal moderation reasons;
- original uploaded media.

Any externally shareable photo must require explicit moderation approval and should be a separate derivative rather than the original private upload.

## Priority 2 — Strengthen the technical demonstration

### 5. Demonstrate real OpenAI use

- Configure a demo deployment with `OPENAI_API_KEY` stored only in the host environment.
- Use the existing server-side Responses API integration with `gpt-5.6`.
- Make the review source visible during the demo (`openai_responses_api` versus deterministic fallback).
- Keep the fallback enabled so the application remains usable if the API is unavailable.
- Never commit keys or include them in screenshots, video, documentation, or test data.

### 6. Make the product experience demo-safe

- Remove or complete every visible inactive button.
- Use one deterministic, rehearsed demo dataset and reset it before recording.
- Keep the primary video journey focused on one strong missing-person case, then briefly show abduction and road-accident targeting.
- Do not claim that the unknown-hospital-patient journey is complete until its dedicated form and verification workflow exist.

## Priority 3 — Devpost presentation and evidence

### 7. Prepare the Devpost page

- Select **Apps for Your Life**.
- Write the description in English.
- Include: problem, audience, solution, AI workflow, safety boundaries, architecture, demo credentials, and roadmap.
- Add 3–5 screenshots that clearly show onboarding, report, AI review, alert feed, moderation, and sharing sheet.
- Link the public code repository.
- Provide the Codex `/feedback` session ID for the thread where most core work was built.
- Include the public YouTube video URL.

### 8. Preserve evidence of hackathon work

- Keep dated commits and the current roadmap/PRD history.
- Preserve the Codex session used to build the core project.
- In the README, clearly describe work added or meaningfully extended during the submission period.

## Deprioritised until after submission

The following work is valuable but should not delay the items above:

- Administration dashboards and hospital-verification workflow (T41–T48).
- Native mobile applications.
- Real payments, Mobile Money, SMS, push notifications, or WhatsApp Business API.
- Authority integrations and public authority-verification badges.
- A complete unknown-hospital-patient reporting workflow.

## Final submission check

- [ ] Public or judge-accessible repository, README, and license.
- [ ] Working URL or reproducible local build with test credentials.
- [ ] All migrations and demo seed steps tested from a clean environment.
- [ ] Public YouTube video under three minutes with audio.
- [ ] Video explains Codex and GPT-5.6 usage.
- [ ] Devpost description and testing instructions are in English.
- [ ] Code repository URL, YouTube URL, and Codex `/feedback` session ID are added to Devpost.
- [ ] No API key, real personal data, or unlicensed asset is included.
- [ ] Printable/PDF/share flow works, or any unfinished capability is honestly identified as roadmap work.
