# SAVE-US — Hackathon Submission Priorities

This checklist prioritises the work that most improves SAVE-US’s OpenAI Build Week submission. It is based on the official requirements and the current MVP state.

## Submission positioning

- **Recommended track:** Apps for Your Life.
- **Core promise:** SAVE-US helps Central African communities structure, review, safely distribute, and share critical emergency alerts.
- **Differentiator:** GPT-5.6 acts as a first-line investigation assistant: it structures reports, identifies missing or inconsistent information, detects possible duplicates, evaluates confidence and fraud risk, and applies country/region targeting rules.
- **Safety statement:** SAVE-US does not verify facts, contact authorities, or replace emergency services. It protects private contacts, exact addresses, coordinates, and original uploaded media.

## Priority 0 — Required before submission

### Current readiness

- Product tasks T1–T54 are complete, including the strengthened T41–T48 administration workflow (private hospital and moderator-access requests, work-inbox notifications, counters, and audit) and the T49–T54 safe sheet/PDF/sharing flow.
- The remaining priorities are operational and submission-focused: stable deployment, real OpenAI demonstration, Devpost video, Devpost page, and hackathon evidence.
- The complete `Unknown hospital patient` journey is deliberately deferred until after submission and must not be presented as available.

### 1. Maintain the README and license — Completed

`README.md`, `README_FR.md`, and the MIT `LICENSE` are present and now document the working alert-sheet and sharing flow, including A4 HTML, server-side PDF, opaque links, WhatsApp/Web Share actions, privacy boundaries, demo access, installation, and tests. Keep these files aligned with any further MVP change before submission.

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
   Demonstrate the printable HTML/PDF sheet and safe WhatsApp sharing with `Source: SAVE-US`; explain that the link is opaque, revocable, and contains no original media.
6. **2:20–2:40 — Multi-event rules**
   Contrast a country-wide suspected abduction with a regional road accident and its expiry.
7. **2:40–2:50 — Codex contribution and impact**
   State how Codex accelerated the MVP and why the approach can scale responsibly across CEMAC.

## Completed PRD promise — Alert sheet, PDF, and secure sharing (T49–T54)

T49–T54 are complete. Published alerts now provide a branded A4 printable HTML sheet, a server-generated PDF, and detail-page sharing actions. The external URL is opaque, revocable, expires after at most seven days or with the alert, and fails after withdrawal, rejection, or expiry. A missing-person or abduction identification photo appears only after explicit reporter authorisation, as a resized metadata-free derivative. Automated E2E coverage checks HTML, extracted PDF text, English attribution, WhatsApp payload, revocation, the authorised derivative, and media/privacy exclusion.

The implemented sheet and external share link never expose:

- private family or reporter contact details;
- exact street address or GPS coordinates;
- private circumstances or internal moderation reasons;
- original uploaded media.

Road-accident media remains excluded from external sharing. Authorised missing-person and abduction identification photos use only a derivative, never the original private upload.

## Completed PRD promise — Responsible administration (T41–T48)

T41–T48 are complete. Administrators have a private workspace to review hospital-verification and reasoned moderator-access requests, manage active moderators with anti-self-lockout safeguards, adjust bounded safety rules, and consult a minimised audit log. Private in-app notifications and role-aware badges surface pending work; the action-first dashboard aggregates moderation volume and delay, active/pending/expired alerts, hospital and moderator-access requests, and moderator activity without exposing private report content. Automated E2E coverage covers the full workflow.

## Priority 1 — Strengthen the technical demonstration

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

## Priority 2 — Devpost presentation and evidence

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
- [x] Printable/PDF/share flow works, includes a safe opt-in photo derivative, and is covered by automated end-to-end safety tests.
- [x] Administrator workflow and access protections are covered by an end-to-end test.
