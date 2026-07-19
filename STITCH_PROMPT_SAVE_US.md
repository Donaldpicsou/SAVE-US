# Prompt for Stitch — SAVE-US templates

Upload the SAVE-US logo before submitting this prompt. Copy everything below into Stitch.

---

Design a complete, responsive web-app template system for **SAVE-US — CEMAC Emergency Network**.

SAVE-US is a community emergency-alert platform for Central Africa. It helps verified citizens report missing persons, suspected abductions, and serious road accidents. Verified hospitals can report unidentified or unconscious patients. AI guides reporting, checks completeness and potential duplicates, assesses fraud risk, and creates alerts for the right country and region.

The Hackathon MVP interface language is **English only**. The first demo country is **Cameroon**, especially the **Centre** region, but the product must visually support all CEMAC countries: Cameroon, Gabon, Equatorial Guinea, Republic of the Congo, Central African Republic, and Chad.

Create a polished, high-trust, mobile-first product that feels calm, civic, protective, and modern. It must not look like a police, military, surveillance, or social-media product. Do not use sensational imagery, graphic injury photos, crime-scene images, or fear-based visual language. Use fictional people and neutral placeholder portraits only.

## Design system

Use the uploaded SAVE-US logo as the brand authority.

- Primary navy: `#003F70`
- Network blue: `#1284BD`
- Soft sky blue: `#86CBE8`
- Primary CTA orange: `#FF6A00`
- App background: `#F7FAFC`
- Text navy: `#0B2740`
- Success: restrained green; warning: amber; danger: red only for blocked/high-risk states.
- Use Inter or a similarly clean sans-serif typeface.
- Use rounded cards, soft shadows, generous spacing, large tap targets, high-contrast text, and clear status chips.
- Use the orange only for urgent primary actions such as “Report an emergency” and “Publish alert”.
- Desktop uses a left navigation rail; mobile uses a bottom navigation bar with Home, Report, Alerts, and Profile.
- Add an always-visible but restrained banner on reporting screens: **“SAVE-US does not replace emergency services. Contact local emergency services immediately when lives are in danger.”**
- Never expose a family phone number, exact street address, or precise GPS coordinates in public templates. Use “Contact family on WhatsApp” and approximate location labels such as “Centre, Yaoundé area”.

## Shared application shell

Create reusable layout components used across all logged-in screens:

- Top header: compact SAVE-US logo, current country selector (“Cameroon”), notification bell, profile avatar.
- Desktop left navigation: Home, Alerts, Report an emergency, My reports, Moderator queue (role-based), Settings.
- Mobile bottom navigation: Home, Report, Alerts, Profile.
- Alert-type badges: Missing person, Suspected abduction, Unknown patient, Road accident.
- Alert-status chips: Draft, AI review, Needs moderation, Published, Rejected, Found, Withdrawn, Expired.
- Common controls: country selector, region multi-select, segmented filters, search field, share button, “Mark as seen” control, safe confirmation modals, loading skeletons, empty states, and error states.

## Create every screen below as an individual, connected template

### 1. Public landing page

Purpose: explain the product and convert a visitor into a signed-in user.

Include:

- Hero with logo, heading **“When every second matters, communities respond.”**, concise description, and orange CTA **“Join SAVE-US”**.
- Secondary CTA **“Browse active alerts”**.
- Emergency disclaimer near the hero.
- Four concise feature cards with icons: Missing people, Suspected abductions, Unknown hospital patients, Serious road accidents.
- “How it works” in three steps: Report, AI review, Geo-targeted community alert.
- CEMAC coverage strip showing six country names, with Cameroon visually active.
- Trust and safety section: verified reporters, AI-assisted checks, privacy-conscious sharing.
- Footer with About, Safety, Privacy, Contact, and “© SAVE-US — CEMAC Emergency Network”.

### 2. Phone sign-in

Purpose: phone-number authentication.

Include:

- Minimal centred card with logo and heading **“Welcome to SAVE-US”**.
- Country calling-code selector set to `+237 Cameroon`.
- Phone number field and CTA **“Send verification code”**.
- Link **“Continue as a demo user”** for the hackathon.
- Privacy note: “Your verified number helps protect the community from misuse.”

### 3. OTP verification

Include:

- Six-digit code input, countdown, resend-code link, change-number link.
- Success state that moves to onboarding.
- Invalid-code error state.

### 4. Onboarding — location

Purpose: collect targeting data.

Include:

- Stepper: `1 Location` → `2 Alert preferences` → `3 Ready`.
- Heading **“Where should SAVE-US protect you?”**
- Country dropdown with all six CEMAC countries; Cameroon selected.
- Region dropdown labelled **“Your primary region”**; Centre selected.
- Supporting text: “You can follow additional regions later.”
- Back and Continue controls.

### 5. Onboarding — alert preferences

Include:

- Four large toggle cards with icons, short descriptions, and enabled/disabled switches:
  - Missing person — “Alerts from your region.”
  - Suspected abduction — “Urgent alerts across your country.”
  - Unknown hospital patient — “Identification requests across your country.”
  - Road accident — “Serious incidents near your followed regions.”
- Multi-select **“Additional regions to follow”** with Littoral and West as sample options.
- E-mail notification toggle.
- Continue CTA.

### 6. Onboarding complete

Include:

- Reassuring illustration using network rings and shield motifs, not emergency imagery.
- Heading **“Your safety network is ready.”**
- Summary: Cameroon · Centre · 2 alert types enabled.
- Primary CTA **“View alerts”** and secondary **“Report a missing person”**.

### 7. Home dashboard / alert feed — populated state

Purpose: primary daily screen for a citizen.

Include:

- Greeting: **“Good morning, Amina”**, location pill `Cameroon · Centre`, and compact **“Report an emergency”** orange CTA.
- Search input: “Search by person or alert ID”.
- Filter chips: All, Missing person, Abduction, Hospital, Road accident; region filter; status filter.
- A highlighted emergency card for a fictional, non-sensitive missing-person alert. Show a neutral portrait, name, age, last seen date, approximate location, status `Published`, and buttons `View alert`, `Share`, `Seen`.
- Additional alert cards in a clear vertical feed.
- Right desktop sidebar / mobile section: “Your alert coverage”, followed regions, preference shortcut, and contribution message: **“Alerts are free. Support SAVE-US from 104 XAF/year.”**
- Include pagination or “Load more alerts”.

### 8. Alert feed — empty state

Include:

- Friendly empty illustration and copy: **“No active alerts match your preferences.”**
- Actions: “Adjust preferences” and “Browse all Cameroon alerts”.

### 9. Alert detail — public safe view

Purpose: help a community member identify, share, and safely respond.

Include:

- Alert ID, alert type, published status, country and approximate region, publication time, and expiry date.
- Neutral fictional portrait and non-sensitive identification data for a missing person: name, age, sex, clothing, last seen date, approximate area, and circumstances.
- Never show a direct family telephone number or precise address.
- Primary CTA **“Contact family on WhatsApp”**, plus Share, Copy link, Mark as seen, and **“Report an issue”**.
- Share bottom sheet/modal with WhatsApp, Facebook, X, and Copy public link. Include fixed attribution text: **“Source: SAVE-US — CEMAC Emergency Network.”**
- Related alert / potential duplicate section only when relevant.
- Safety disclaimer and status timeline.

### 10. Select report type

Purpose: starting point for a new report.

Include four large selectable cards:

- **Report a missing person** — “Help find someone who has disappeared.”
- **Report a suspected abduction** — “Share urgent, verified information country-wide.”
- **Report a road accident** — “Help nearby people respond to a serious crash.”
- **Report an unknown hospital patient** — locked for citizens, with badge **“Verified hospitals only”** and link “How hospital verification works”.

Add a prominent safety warning and a low-emphasis **“Save and finish later”** action.

### 11. Missing-person report form

Purpose: the core MVP template.

Create a multi-step form with progress indicator and save-draft support.

**Step A — Person**

- Full name *required*
- Age *required*
- Sex *required*
- Clear photo uploader *required*

**Step B — Last known information**

- Date last seen *required*
- Region and approximate last-seen location *required*
- Clothing description optional
- Circumstances optional

**Step C — Family contact and consent**

- Family contact, stored privately *required*
- WhatsApp available toggle
- Consent checkbox confirming the reporter can submit the information

Use clear required markers, inline validation, photo guidance, and a final CTA **“Review with SAVE-US AI”**.

### 12. Missing-person report — draft / validation state

Include:

- Saved-draft banner with timestamp.
- Inline errors for missing required data.
- A secure photo-upload error state.
- CTA disabled until required fields are complete.

### 13. AI review — loading state

Purpose: make AI activity visible without overclaiming.

Include:

- Calm full-page progress state with shield/network animation.
- Copy: **“SAVE-US AI is checking the report for completeness and possible duplicates.”**
- Progress steps: Structuring report → Checking consistency → Comparing active alerts → Preparing alert summary.
- Avoid showing opaque reasoning, percentages, or technical model language during loading.

### 14. AI review — cleared for publication

Purpose: the most important decision template.

Include:

- Heading **“This report is ready to help the community.”**
- Published-ready status and a readable AI-generated public summary.
- Sections: Information captured, Missing information (if any), Possible duplicates, Safety checks.
- Two distinct score cards:
  - **Report confidence: 92/100** with explanation “Information is complete and consistent.”
  - **Fraud risk: Low** with explanation “No strong indicators of deceptive reporting found.”
- Distribution panel: `Cameroon` → `Centre region` → estimated eligible recipients.
- Primary orange CTA **“Publish alert”** and secondary **“Edit report”**.
- A note: “AI helps structure and review reports. SAVE-US does not confirm facts or replace emergency services.”

### 15. AI review — needs moderator / blocked state

Create two visual variants within the same template family:

- **Possible duplicate:** show a restrained amber warning, one or two matching alert cards, and CTA **“Send for moderator review”**. Do not auto-publish.
- **High fraud risk or unsafe media:** show clear but respectful red blocking state, a plain-language reason, secure action **“Edit report”**, and message **“This report has been sent for human review.”** Do not expose score mechanics beyond “High risk”.

### 16. Alert published success

Include:

- Success illustration and heading **“Alert published for Centre, Cameroon.”**
- Share-ready alert preview card.
- Buttons: `Share on WhatsApp`, `Copy public link`, `Download alert sheet (PDF)`, `View alert`.
- Distribution summary: country, region, enabled recipients, expiry date.
- Reminder: “If the person is found, update this alert immediately.”

### 17. My reports dashboard

Purpose: help reporters manage reports after publication.

Include:

- Tabs: Active, Drafts, Needs review, Closed.
- Report cards with type, subject/name, status, last update, expiry, and contextual action.
- Available contextual actions: View, Edit draft, Renew (hospital only), Mark as found, Withdraw alert.
- A simple activity timeline per report.

### 18. Close or withdraw alert modal

Create two safe, clear confirmation modals:

- **Mark person as found:** confirmation, optional contextual note, primary CTA “Confirm found”.
- **Withdraw alert:** required reason textarea, privacy reminder, CTA “Withdraw alert”.

Show the public result state as `Found` or `Withdrawn`; preserve a non-public audit record in the product concept.

### 19. Report an issue / suspected false alert

Include:

- Reason selector: Incorrect information, Person has been found, Possible false alert, Privacy concern, Other.
- Free-text explanation, optional evidence upload, safe warning against harassment.
- CTA **“Submit report for review”**.
- Confirmation state explaining that a moderator will review it.

### 20. Settings and alert preferences

Include sections for:

- Profile: verified phone, country, primary region.
- Followed regions multi-select.
- Alert-category toggles.
- E-mail notifications toggle.
- Support card: **“Emergency alerts stay free. Support SAVE-US from 104 XAF/year.”** with a non-functional “Support SAVE-US” button marked “Coming soon”.
- Account actions and privacy link.

### 21. Moderator queue

Purpose: operational template for approved moderators.

Include:

- Counts: High risk, Possible duplicates, Removal requests, Unreviewed.
- Filterable table/list with report ID, type, country/region, reporter verification, submitted time, reason for review, and status.
- Review detail pane showing safe report data, AI review summary, duplicate candidates, media moderation result, and audit timeline.
- Actions: Publish, Reject, Request changes, Suspend reporter. Require a confirmation modal and a reason for destructive actions.
- Keep the tone factual and non-accusatory.

### 22. Hospital representative report template

Purpose: secondary MVP / future-ready interface.

Include verified-institution badge and fields:

- Patient photo only if appropriate and consent is possible
- Age range *required*
- Sex *required*
- Distinguishing mark *required*
- Hospital *required*
- Hospital service contact *required*
- Optional identity-card information
- Publish reach: entire country
- Expiry: 3 days; renewable by hospital

### 23. Road-accident report template

Purpose: secondary MVP / future-ready interface.

Include:

- Approximate GPS location *required*, shown with a privacy-safe map preview
- Optional photo/video upload with notice: “Graphic media may be rejected.”
- Optional number of victims and immediate need: ambulance, police, towing, other
- Region/radius distribution selector
- Expiry default: 24 hours
- CTA **“Review with SAVE-US AI”**

### 24. Notification templates

Create two compact templates:

- In-app notification centre with unread/read states and alert-type icons.
- Responsive email alert: logo, alert type, short safe summary, approximate location, time, `View alert` CTA, and source attribution. Do not include private phone numbers or precise location.

## Prototype connections

Connect this principal click path:

Landing → Phone sign-in → OTP → Onboarding location → Preferences → Onboarding complete → Alert feed → Report an emergency → Missing-person form → AI loading → AI cleared review → Publish success → Public alert detail → Share modal → My reports → Mark as found modal.

Also connect the AI cleared-review screen to the possible-duplicate/high-risk blocked variants and then to the Moderator queue.

## Final output requirements

- Generate desktop and mobile variants for the most important screens: landing, sign-in, onboarding, feed, missing-person report, AI review, public alert detail, and settings.
- Maintain a coherent reusable component system across every screen.
- Use realistic English copy and Cameroon/Centre demo data, but fictional names and images.
- Clearly differentiate public, reporter, hospital, and moderator experiences through navigation and permissions, not through radically different branding.
- Prioritize the missing-person flow visually because it is the Hackathon demo path.
- Do not design payments, native mobile flows, public comments, real-time maps, or authority integrations for this MVP.

---
