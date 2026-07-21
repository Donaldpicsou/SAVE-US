# SAVE-US — CEMAC Emergency Network

SAVE-US is a safety-first civic emergency-alert MVP for Central Africa (CEMAC). It helps communities structure, review, target, and safely distribute critical reports when traditional information channels are too slow to coordinate.

Built for **OpenAI Build Week 2026**, SAVE-US is submitted in the **Apps for Your Life** track.

> SAVE-US does not replace police, ambulance, fire, hospital, or other emergency services. When a life is in immediate danger, contact local emergency services first.

## The problem

Across the CEMAC region, families, witnesses, and care teams may struggle to centralise and circulate time-sensitive information about missing people, suspected abductions, unidentified patients, and serious road accidents. Informal sharing can be slow, geographically irrelevant, and vulnerable to misinformation or privacy harm.

SAVE-US addresses this gap with an English-language web MVP that:

- guides a verified reporter through structured incident information;
- uses GPT-5.6 to produce a safe public summary and flag missing data, possible duplicates, confidence, and fraud risk;
- applies explicit publication rules and human moderation safeguards;
- sends only eligible users the alerts that match their country, region, and category preferences;
- retains an accountable private audit trail for sensitive lifecycle decisions.

The MVP demonstration is centred on Cameroon and the Centre region while retaining CEMAC country and region data.

## Current MVP features

### Reporting and review

- Simulated phone-number authentication with OTP verification.
- CEMAC phone-number validation and country/primary-region onboarding.
- Alert preferences: categories, followed regions, and simulated e-mail preference.
- Guided, resumable reporting journeys for:
  - Missing people;
  - Suspected abductions;
  - Serious road accidents.
- Server-side validation, local private photo storage, and safe report drafts.
- Structured AI review for missing-person and suspected-abduction reports:
  - public-safe English summary;
  - extracted data and missing fields;
  - possible duplicate candidates;
  - confidence and fraud-risk scores;
  - explicit reasons and publication decision.
- GPT-5.6 visual safety review for optional road-accident media when an API key is configured.

### Safety, publication, and targeting

- Publication safeguards: alerts publish only when the relevant rules pass; otherwise they are routed to moderation.
- Missing-person alerts target eligible users in the affected region and followed regions.
- Suspected-abduction alerts target eligible subscribers across the affected country.
- Road-accident alerts target eligible regional subscribers, expire after 24 hours, and may be closed early with a reason.
- In-app publication, moderation, closure, and expiry notifications with read state.
- Moderator workspace for private review, reasoned publication, information requests, rejection, and post-publication abduction withdrawal.
- Private audit entries for report closures and moderation decisions.
- Restricted administration workspace: private hospital-verification review, reasoned moderator-access requests and protected role changes, bounded future-facing safety rules, searchable minimised audit log, private operational notifications, role-aware pending-work badges, and an action-first aggregate dashboard.

### Product experience

- Responsive SAVE-US visual identity, shared navigation, footer, notification menu, and account menu.
- Home dashboard, full alert feed, alert details, notification centre, and reporter workspace.
- Authorised English alert sheets: branded A4-printable HTML and server-generated PDF from one public-safe contract. Missing-person and abduction identification photos appear only after explicit reporter authorisation, as a resized metadata-free derivative.
- Secure alert sharing from the detail page: copy-link, Web Share with clipboard fallback, and a prefilled WhatsApp message containing `Source: SAVE-US` and an opaque URL. The secure share page supplies an approved photo preview for supported social networks when one is authorised.
- Opaque share links are revocable, expire within seven days (or sooner with the alert), and stop working when an alert is withdrawn, rejected, or expired.
- CEMAC reference data and seeded demo users.
- Automated tests for reporting, AI contracts, targeting, notifications, protected media, moderation, sheets, sharing, and end-to-end journeys.

## Known MVP limits

- The app is a hackathon demonstration, not a substitute for emergency services or authorities.
- OTP, e-mail, and notifications are simulated; there is no live SMS, push, or WhatsApp Business integration.
- The `Unknown hospital patient` alert type exists in the domain model and preferences. Hospital-verification requests and administrator approval are implemented, but the dedicated patient-reporting, renewal, and publication journey is not yet implemented.
- Payments, Mobile Money, authority integrations, real-time maps, native mobile apps, and public comments are out of scope.
- AI output assists first-line review; it does not establish facts or contact authorities.
- External sharing never includes the original uploaded photo. An explicitly authorised missing-person or abduction identification photo is transformed into a resized, metadata-free JPEG derivative for the sheet, PDF, and secure share page. Road-accident media remains excluded from external sharing by default.

## Technology and architecture

SAVE-US is a Flask application with a deliberately small, testable architecture:

| Layer | Implementation |
|---|---|
| Web application | Flask 3 and Jinja templates |
| Persistence | SQLite with SQLAlchemy and Flask-Migrate |
| Authentication | Simulated phone/OTP session authentication |
| Media | Private local storage outside `static/`, with server-side validation |
| AI review | OpenAI Responses API with GPT-5.6 and structured output validation |
| AI resilience | Deterministic, transparent demo fallback when an API key or API response is unavailable |
| Alert sheets and sharing | Versioned public-safe contract, A4 HTML, server-side PDF, opt-in metadata-free photo derivatives, opaque revocable/expiring share links |
| Tests | Python `unittest` suite |

### High-level flow

```text
Verified reporter
  → structured incident report
  → GPT-5.6 review or deterministic fallback
  → publication rule / human moderation
  → country- or region-targeted alert
  → eligible recipient notification and alert feed
```

## Privacy and safety choices

SAVE-US is intentionally designed around data minimisation and accountable decisions.

- **Protected media:** uploaded photos are stored privately and are served only to the reporter, eligible recipient, or authorised moderator. Unauthorised media requests return `404`; responses are private and non-cacheable.
- **Authorised share photos:** only missing-person or abduction identification photos with explicit reporter permission may appear externally. SAVE-US creates a resized JPEG derivative without EXIF metadata; its token-bound route stops working when sharing is revoked or the alert is withdrawn, rejected, or expires. Road-accident media is never externally shared by default.
- **No public private contacts:** family and reporter contact fields never appear in public alert content.
- **Approximate public location:** public alerts use an approximate area or region; precise street addresses and GPS coordinates remain private.
- **Preference-based targeting:** recipients must have a verified phone, matching country, enabled category, and—where relevant—matching or followed region.
- **Human safeguards:** high-risk, incomplete, duplicate, or sensitive reports can be routed to a moderator.
- **Audit trail:** reasoned closure, moderation, hospital-verification, moderator-role, and safety-rule actions retain accountable private audit metadata. Administrators can search a minimised view without exposing private report content.
- **Media safety:** potentially graphic, invalid, or uncertain road-accident media is blocked or sent to moderation rather than being automatically published.
- **Safe external sharing:** printable sheets, PDFs, and external links consume only the public-safe alert-sheet contract. They exclude original media, private contacts, exact addresses/GPS, private circumstances, and internal moderation reasons. A permitted identification-photo derivative is the sole exception; shared-link responses are non-cacheable and links can be revoked.

## Quick start

### Prerequisites

- Python 3.11 or newer.
- `pip` and a terminal.
- Optional: an OpenAI API key to run live GPT-5.6 review. The deterministic demo fallback works without one.

### 1. Clone and create the virtual environment

```bash
git clone https://github.com/Donaldpicsou/SAVE-US.git
cd SAVE-US
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies and configure local variables

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` only if you want live AI review:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6
OPENAI_MEDIA_MODEL=gpt-5.6
```

Never commit `.env` or an API key. Without `OPENAI_API_KEY`, SAVE-US uses its deterministic demo fallback.

### 3. Create and seed the database

Use the migrations for a normal local setup:

```bash
.venv/bin/flask --app run:app db upgrade
.venv/bin/python scripts/seed_demo_data.py
```

The seed command is idempotent: it can be run again without duplicating demo users or preferences.

### 4. Run locally

```bash
.venv/bin/flask --app run:app run --debug
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### Alternative local table creation

For a minimal local demonstration database, the following helper creates tables from the current SQLAlchemy metadata:

```bash
.venv/bin/python scripts/init_db.py
.venv/bin/python scripts/seed_demo_data.py
```

Prefer Alembic migrations for normal development and deployment.

## Demo access

All seeded phones use the simulated OTP code:

```text
123456
```

Useful demo accounts:

| Role | Name | Phone number | Country / region |
|---|---|---|---|
| Reporter | Amina N. | `+237612345678` | Cameroon / Centre |
| Citizen subscriber | David T. | `+237677123456` | Cameroon / Centre |
| Moderator | Clarisse M. | `+237655334455` | Cameroon / Centre |
| Administrator | SAVE-US Admin | `+237690001122` | Cameroon / Centre |
| Regional subscriber | Jonas K. | `+237688445566` | Cameroon / Littoral |
| CEMAC subscriber | Paul E. | `+24174001122` | Gabon / Estuaire |

To sign in, select the matching calling code, then enter the national part of the number without it (for example, select **(+237) 🇨🇲** and enter `612345678` for Amina N.). You may also paste the complete international number. Then enter `123456` on the OTP page, provide the required display name, and choose the country and primary region.

## Testing

Run the complete automated test suite from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -q
```

The suite covers model validation, OpenAI contract validation, deterministic fallback, targeted delivery, protected media access, reporting flows, moderation decisions, Cameroon/Centre end-to-end journeys, administration permissions and workflow (including private request notifications and pending-work counters), and sheet/sharing safety. The sharing E2E tests extract generated PDF text and verify English attribution, WhatsApp payload construction, link revocation, and the absence of private data or unapproved media.

## Built with Codex and GPT-5.6

SAVE-US was built and meaningfully extended during OpenAI Build Week 2026 with Codex as the implementation collaborator and GPT-5.6 as the structured review engine.

### How Codex accelerated the project

Codex helped accelerate:

- Flask project setup, application structure, migrations, SQLAlchemy entities, and test scaffolding;
- the Stitch-derived visual integration, responsive shared shell, navigation, notification menus, and accessibility-oriented interaction refinements;
- reporting workflows, validation rules, protected media handling, CEMAC data seeding, targeting logic, moderation workspace, and restricted administration tools;
- regression tests and end-to-end scenario coverage;
- public-safe A4/PDF alert-sheet delivery, opaque share links, and safe sharing controls;
- PRD, roadmap, submission checklist, and repository documentation.

### Deliberate team decisions

The project team made the key product and engineering decisions, including:

- choosing a safety-first community coordination model rather than claiming authority verification;
- differentiating country-wide suspected-abduction targeting from regional missing-person and road-accident targeting;
- keeping private contact data, exact location, and original media outside public alert content;
- using explicit publication thresholds and retaining human moderation for sensitive cases;
- keeping an offline deterministic fallback so the hackathon demo remains reliable.

### How GPT-5.6 is used

When `OPENAI_API_KEY` is configured, the server calls the OpenAI Responses API using GPT-5.6. The application validates structured responses before persisting them. GPT-5.6 produces a public-safe summary, extracted data, missing fields, possible duplicates, confidence score, fraud-risk score, decision, and reasons for missing-person and suspected-abduction reports.

For optional road-accident media, GPT-5.6 performs a structured visual safety check. Invalid, graphic, or unsafe media is blocked; uncertain media is routed to human moderation. Private contact data is excluded from the abduction AI input, and public summaries are validated to reject phone numbers.

### Reliable fallback behaviour

If no API key is configured, the OpenAI package is unavailable, a request fails, or a structured response is invalid, SAVE-US uses a deterministic fallback. The fallback is explicitly identified as demo logic and does not claim factual verification. It allows the same reporting, safety, moderation, and targeting journey to remain runnable offline.

## Hackathon provenance

The repository’s dated commit history records the project work completed during the hackathon submission period, including the PRD, English PRD, roadmap, Flask MVP, reporting flows, structured GPT-5.6 review, road-media moderation, targeting, notification centre, multi-event end-to-end tests, human moderation, operational administration inbox workflows, and public-safe alert sheets and sharing.

SAVE-US is original work created and meaningfully extended for OpenAI Build Week 2026. Any open-source dependencies are used under their respective licences. The repository does not include an OpenAI API key or other production credential.

## Roadmap

Near-term planned work is documented in:

- [English roadmap](RoadMap-SAVE-US_EN.md)
- [French roadmap](RoadMap-SAVE-US.md)
- [English submission priorities](SAVE_US_Submit_required_EN.md)
- [French submission priorities](SAVE_US_Submit_required.md)

All planned MVP tasks T1–T54 are complete. The next product work is the post-submission unknown-hospital-patient journey, detailed as T55–T59 in the roadmaps; deployment, video, and Devpost preparation remain the immediate submission priorities.

## License

This project is released under the [MIT License](LICENSE).
