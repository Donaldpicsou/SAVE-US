# SAVE-US — Hackathon MVP PRD

**Product:** SAVE-US, CEMAC Emergency Network  
**Version:** OpenAI Build Week Hackathon MVP  
**Date:** July 21, 2026
**MVP interface language:** English only  
**Demo market:** Cameroon; architecture and country picker ready for all six CEMAC countries  
**Devpost target:** *Apps for your life*

**Change control:** Any approved change that alters the product intent, user promise, scope, safety rule, or acceptance criteria must update this PRD and both roadmap files. Implementation refinements that already satisfy this PRD are recorded in the roadmaps only.

## 1. Executive summary

SAVE-US is a community-led emergency alert and verification platform for the CEMAC region. Verified citizens can report missing persons, suspected abductions, and serious road accidents. Verified medical institutions are the role planned for the future unidentified, amnesiac, or unconscious-patient journey.

AI agents structure reports, identify missing or inconsistent information, detect possible duplicates, assess fraud risk, and generate a shareable alert sheet. Alerts are targeted by country, region, and user preferences so that critical information travels quickly without overwhelming people with irrelevant notifications.

The MVP primarily demonstrates a missing-person journey in Cameroon while also including suspected-abduction and road-accident journeys, human moderation, restricted administration, and safe public sharing. The dedicated unknown-hospital-patient journey remains deferred until after the hackathon.

## 2. Problem and value proposition

Critical information often arrives late, is fragmented, and lacks a consistent verification process. SAVE-US provides a civic first layer. It is neither an emergency service nor an investigative authority. It accelerates structured reporting, improves consistency, and responsibly distributes alerts to people most likely to help.

**Promise:** a clear alert, reviewed by AI under explicit rules, delivered to the right community, and immediately shareable.

## 3. MVP objectives

1. Allow a signed-in citizen to submit a missing-person report in Cameroon.
2. Make the AI review understandable: extracted data, missing fields, possible duplicates, confidence score, and fraud-risk score.
3. Publish an alert when it satisfies the confidence and safety rules.
4. Target subscribers in the relevant country and region according to their preferences.
5. Generate an English printable/PDF alert sheet and share links.
6. Demonstrate the three operational journeys (missing person, suspected abduction, and road accident); keep the unknown-hospital-patient journey as an explicitly deferred evolution.

### Demo success metrics

- A complete report becomes a published alert in under three minutes.
- AI explains the result without exposing internal reasoning: status, missing fields, potential duplicate, and blocking reasons.
- At least one demo recipient receives the alert in the feed and through a simulated email.
- WhatsApp sharing and the public link automatically include “Source: SAVE-US”.

## 4. Scope

### Included in the MVP

- Responsive English-language web application.
- Phone-number sign-up with simulated OTP for the hackathon.
- A required privacy-respecting display name, then a profile with country, primary region, additional followed regions, and enabled alert categories.
- Full CEMAC country/subdivision catalogue supplied by the project owner.
- Geo-targeted alert feed and simple search by name/status.
- Complete missing-person, suspected-abduction, and road-accident reporting flows; the unknown-hospital-patient journey is deferred.
- AI review, duplicate detection, lightweight moderation, alert-sheet generation, and sharing with opt-in safe identification-photo derivatives for missing-person and abduction alerts.
- Restricted administration: private hospital verification, reasoned moderator-access requests and role management, bounded safety rules, audit log, and an aggregate operational dashboard with a private work inbox and action counters.
- Alert status, false-alert/error reporting, and reporter-initiated withdrawal with a reason.
- Demo email and in-app notification centre.
- Prominent emergency-services disclaimer.

### Not included in the MVP

- Live 104 XAF payment, Mobile Money, and telecom integrations.
- SMS, native push notifications, WhatsApp Business API, or authority integrations.
- Native iOS/Android apps.
- Detailed real-time map; the alert feed is the primary MVP view.
- “Verified by authorities” badge, public comments, or an internal social network.
- Real hospital publication without prior manual institutional verification.
- Dedicated unknown-hospital-patient reporting and publication, including hospital renewal.

## 5. Users and permissions

| Role | MVP permissions |
|---|---|
| Citizen / subscriber | View alerts, manage alert preferences, mark “seen”, share, and report an error. |
| Reporter | A citizen with a verified phone number; creates missing-person, abduction, and road-accident reports. |
| Hospital representative | Institution manually verified through documentation; role ready for the future unidentified-patient journey. |
| Moderator | Reviews high-risk reports, duplicates, and removal requests; decides on publication or suspension. |
| Administrator | Verifies hospitals, manages moderators, and manages rules. |

One person can be both a citizen and a reporter. Viewing and receiving alerts remain free; the product displays a non-blocking invitation to support SAVE-US at **104 XAF/year**.

## 6. Alert types and distribution rules

| Type | Who can create it | Minimum data | Default reach | Expiration |
|---|---|---|---|---|
| Missing person | Verified phone user | Name, age, photo, sex, date, last-seen location, family contact | Relevant region; other regions only when followed | 7 days |
| Suspected abduction | Verified phone user | Location, date/time, description; photo is optional and validated when provided | Entire country | 30 days |
| Unknown hospital patient | Verified hospital | Age range, sex, distinguishing mark, hospital, service contact; photo when possible | Entire country | Deferred after the hackathon: 3 days; renewable by hospital |
| Serious road accident | Verified phone user | GPS location; photo/video, victim count, and immediate need are optional | Accident region or geographic radius | 24 hours by default; manual closure allowed |

The 24-hour road-accident expiration is an MVP scoping decision because no duration was specified. It must be validated with future emergency-service partners.

## 7. Targeting and preferences

During sign-up, a user chooses a required responsible display name, then selects one country and one primary region. They may later change the display name, country, and region, follow extra regions, and enable or disable each alert category.

Recipient selection rules:

1. The alert’s country must match the recipient’s selected country.
2. For missing persons and accidents, the recipient must follow the affected region, or be within the defined radius when one exists.
3. For abductions, every in-country user who enabled that category is eligible. The unknown-hospital-patient rule is reserved for the deferred journey.
4. An explicit opt-out always overrides other conditions.

## 8. AI workflow and publication decision

### First-line agent

The assistant guides the reporter, asks for the required information, converts answers into structured fields, and requests missing details. It then produces a public English summary and a search/alert sheet.

### AI checks

- Completeness and consistency checks: age, dates, country/region, and contact formats.
- Active-alert duplicate search based on name, age, photo, and last known location.
- Accident photo/video moderation: graphic or disturbing content is rejected with a simple explanation.
- Two independent scores:
  - **Confidence score:** quality and consistency of a report. Automatic publication is possible at **80/100 or above**, subject to all safety rules.
  - **Fraud-risk score:** likelihood that a report is deceptive. At **80/100 or above**, publication is automatically blocked and the case is routed to a moderator.

AI never contacts an authority and never claims to verify facts. Blocked cases, possible duplicates, and sensitive alerts are visible in the moderator queue. A suspected abduction with a confidence score of at least 80 may be published immediately country-wide, while still being queued for post-publication moderation.

## 9. Primary demo journey

1. **Onboarding** — Amina creates an account using a simulated Cameroonian phone number, selects Cameroon and Centre, and enables Missing person and Suspected abduction alerts.
2. **Report missing person** — A family provides required information and uploads a photo.
3. **AI review** — SAVE-US displays extracted data, highlights missing information if any, compares active alerts, and shows both scores.
4. **Publish** — If all checks pass, the alert is published to Centre. A PDF sheet and sharing link are generated; an identification photo is included only when the reporter explicitly authorises its safe public derivative.
5. **Receive and share** — Amina sees the alert in her feed, receives a demo email, marks it as seen, and opens a prefilled WhatsApp share with SAVE-US attribution.
6. **Close the loop** — The reporter can mark the person as found or withdraw the alert with a reason; the public status updates.

## 10. MVP screens

1. Landing page: mission, emergency disclaimer, “Join SAVE-US” CTA.
2. Phone sign-in / OTP.
3. Onboarding: country, region, and alert preferences.
4. Alert feed: country/region/type/status filters and alert cards.
5. New report: alert-type selection, guided assistant, and structured form.
6. AI review: summary, detected data, checks, scores, and decision.
7. Public alert detail: safe information, status, sharing, “Seen”, and error reporting.
8. Reporter dashboard: submitted alerts, renewal, reasoned withdrawal, and “Found”.
9. Moderator queue: blocked and high-risk items.
10. Settings: primary country/region, followed regions, categories, and contribution reminder.
11. Administration: private hospital verification, moderator-access requests and management, safety rules, audit log, private operational notifications, and an aggregate dashboard restricted to administrators.

## 11. Safety, privacy, and responsible use

- Display on every reporting flow: “SAVE-US does not replace emergency services. Contact local emergency services immediately when lives are in danger.”
- Do not display the family phone number; offer a controlled WhatsApp/“Contact family” action instead.
- Do not publish a precise street address or exact GPS coordinates. Show an approximate area or region publicly; retain precise data for the reporter and moderators only.
- For minors and unknown patients, expose only what is necessary for identification; use a photo only when publication is justified.
- Missing-person and abduction identification photos require explicit reporter authorisation before appearing in a sheet, PDF, or secure share page. SAVE-US uses a resized metadata-free derivative, never the original upload; authorisation can be withdrawn while the report is a draft.
- Road-accident media remains excluded from external sharing by default, even after its private moderation workflow. Unknown-patient media remains deferred and private by default.
- Disable public comments. Users can share, mark an alert as seen, and report an error with evidence.
- Require a reason before withdrawal. Keep a non-public audit log containing author, dates, scores, decision, and justification.

## 12. Core data model

| Entity | Key fields |
|---|---|
| User | id, verified phone, role, country, primary region, contribution status |
| AlertPreference | user_id, enabled categories, followed regions, email enabled |
| Alert | id, type, status, country, region, approximate zone, reporter, dates, expiry, public content |
| MissingPersonDetails | name, age, sex, private photo, explicit public-media authorisation, last seen, date, clothing, private contact, circumstances |
| AIReview | alert_id, summary, missing data, duplicate candidates, confidence_score, fraud_risk_score, decision, reasons |
| Media | alert_id, private path, type, moderation result, optional public rendition |
| Notification | recipient, alert, channel, delivery/read status |
| ReportAction | withdrawal, found, correction, false-alert report, and moderation decisions; private reason |
| HospitalVerificationRequest | private institution request, reviewer, decision, and reason |
| ModeratorAccessRequest | private applicant reason, status, reviewer, decision, and reason |
| Notification | private recipient item; operational items reference only the authorised administrative request |
| SafetyRule / AdministrationAuditEntry | bounded threshold, actor, action, prior/new value, immutable reason, and authorised request reference |

Alert statuses: `draft`, `ai_review`, `needs_moderation`, `published`, `rejected`, `reported_found`, `withdrawn`, `expired`.

## 13. Recommended architecture

### Recommendation: Flask monolith for the hackathon

| Layer | Proposal |
|---|---|
| Web | Flask + Jinja templates + Bootstrap or Tailwind via CDN |
| Data | SQLite + SQLAlchemy with seeded demo data |
| Auth | Simulated OTP, designed for a future Firebase Authentication integration |
| AI | Server-side OpenAI Responses API for structured extraction, summary, duplicate detection, and JSON decision output |
| Media | Local demo storage with an abstraction ready for Cloudinary/S3 |
| PDF | HTML/CSS-to-PDF or server-side alert-sheet generation |
| Email | Test SMTP/local console with demo recipients |

**Why Flask:** it is fast for a solo developer, has few conventions, and is well suited to a server-rendered Jinja flow and an integrated demo.  
**Trade-off:** it provides fewer built-in administration capabilities than Django, and the API/mobile separation should be strengthened after the hackathon.

### Alternatives considered

| Stack | Strengths | Weaknesses within this deadline |
|---|---|---|
| Django | Full admin, authentication, and ORM | More setup and conventions to absorb in two days |
| FastAPI + React | Typed API; strong future API/mobile base | Two layers to build; slower pace for one person |
| Next.js + Supabase | Modern web product; quick cloud auth/data | Higher stack-change and cloud dependency risk |

## 14. MVP visual identity

The supplied logo is the visual authority. The interface should convey protection, connection, and urgency without feeling alarming.

| Use | Suggested colour |
|---|---|
| Primary / protection | Navy `#003F70` |
| Secondary / network | Blue `#1284BD` |
| Soft information | Sky `#86CBE8` |
| Urgency and primary action | Orange `#FF6A00` |
| Background | Off-white `#F7FAFC` |
| Text | Navy `#0B2740` |

- Typeface: Inter or a system sans-serif; sharp, readable mobile headings.
- Primary button: orange; normal actions: navy.
- Danger red is reserved for blocking or risk, never merely for an active alert.
- Alert cards show type, status, country/region, date, a respectfully cropped photo, and sharing CTA.
- Display the logo on the landing page and header; use its compact version as favicon/app mark.

## 15. Two-day delivery plan

### Day 1 — happy path

1. Bootstrap Flask, styles, and CEMAC data.
2. Build onboarding, profile, and preferences.
3. Build the Missing person flow, Alert model, and targeted feed.
4. Integrate AI review with a seeded demo fallback.

### Day 2 — product proof and submission

1. Add sharing, PDF sheet, simulated email, “Seen”, withdrawal, and error reporting.
2. Add secondary forms and the moderator queue.
3. Verify safe public data, AI blocking cases, and responsive behaviour.
4. Prepare a 2–3 minute demo video, screenshots, and Devpost submission.

## 16. Acceptance criteria

- A new user cannot complete registration without a display name between 2 and 120 characters; they can later change it from Profile & account.
- A user can choose Cameroon/Centre and later change country, region, and preferences.
- A missing-person report cannot be submitted without required fields.
- A report with confidence score ≥ 80 and fraud-risk score < 80 can be published.
- A report with fraud-risk score ≥ 80 is blocked and visible only in the moderator queue.
- A possible duplicate cannot be auto-published.
- A published missing-person alert is delivered only to eligible users in the same country and followed regions.
- The family phone number and precise location are never publicly exposed.
- The share link includes SAVE-US attribution.
- A sheet, PDF, or secure share page may include only an explicitly authorised, metadata-free identification-photo derivative for a missing-person or abduction alert; road-accident and original media remain excluded.
- An alert can be reported, withdrawn with a reason, marked “found”, and expired according to its category.
- Sensitive administration actions require a reason, are audited, and remain administrator-only.
- Administrators receive private in-app notifications for pending hospital-verification and moderator-access requests; the workspace and navigation show only aggregate pending counts and clear them once the underlying request is decided.

## 17. Post-hackathon roadmap

- French, Spanish, then local languages.
- Real Firebase Authentication, Mobile Money, and telecom operators.
- Mobile apps and push/SMS/WhatsApp Business notifications.
- Mapping, geographic radii, and hospital/authority integrations.
- Authority verification and official badge.
- Complete unknown-hospital-patient journey: verified-hospital-only report, review, country-wide publication, expiry, and renewal.
- Data-retention policy, institutional agreements, and local legal review in every CEMAC country.
