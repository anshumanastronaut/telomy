# Telomy Market-Intelligence — Findings Log (append-only)

Each entry: platform · basic features · advanced features · pricing · weaknesses · **what Telomy
should integrate**. Seeded below.

---

## 2026-10-20 — Seed: global longevity leaders & India health apps

**Function Health** — broadest panel (160+ biomarkers incl. ApoB, Lp(a)), flat **$365/yr**, 2,000+
collection sites; report leans on AI recommendations. Basic: panel+records+report. Advanced: breadth,
distribution. *Weakness:* AI guidance is generic/ungrounded.

**InsideTracker** — personalization play: ~43–54 markers + **DNA + fitness-tracker integration + a
biological-age score**; pricing inconsistent ($149/yr membership to ~$340 panel).

**Superpower** — value entry **$199/yr**, 100+ markers, biological-age score, **clinician pathway for
TRT/GLP-1/HRT/peptides**; wearable integration costs extra.

**Neko Health / Prenuvo** — in-clinic full-body scan model (Neko: 1-hr visit, proprietary sensors,
immediate results + clinician chat). Capital-heavy; limited scale.

**India — Tata 1mg / Practo** — omnichannel: e-pharmacy + home lab tests + online consults + digital
records (+ physical pharmacies for 1mg). Practo Plus ~₹2,999/yr. Strong on logistics, light on
longevity science.

**India — HealthifyMe** — nutrition leader: AI plan from ~₹208/mo, human-coach add-ons, **CGM option
(~₹4,099)**, meal-photo AI. **Cult.fit** — fitness classes (₹999–3,999). **Ultrahuman** — ring + glucose
biomarkers + coaches.

**Standout opportunities for Telomy:** (1) We beat all of them on *advanced* science — trained
disease/mortality prediction, multimodal bloods×wearables fusion, grounded on-device AI, muscular age,
and a safety agent — none of the longevity players have this stack. (2) Close *operational* parity via
partnerships, not R&D: lab home-collection (like Function/1mg), e-pharmacy + Rx pathway (like 1mg/
Superpower), CGM (like HealthifyMe/Ultrahuman). (3) India wedge: no one pairs 1mg-style logistics with
Function-style longevity science and on-device privacy — that's open ground.

Sources: finvsfin & surges biomarker comparisons; manopausemd longevity providers; newmarketpitch Neko;
Tata 1mg (Wikipedia); Practo/HealthifyMe/Cult.fit 2026 pricing guides.

---

## 2026-10-21 — Lifeforce

US telehealth longevity clinic, founded 2021 by Tony Robbins, Peter Diamandis, Dugal Bain-Kim and Joel
Jackson. Last round we could find: a $12M Series A in 2023 (M13, Peterson Ventures). We found no 2026
funding or launch news. It sells **memberships built around hormone and therapy prescriptions**, not
breadth of diagnostics.

**Basic features.** A 50+ biomarker panel in six groups (hormones, nutrients, metabolic, organ, cardio,
other risk). That is narrower than Function (160+) or Superpower (100+). Blood is drawn by a mobile
phlebotomist at home or at a lab, 2× or 4× a year depending on tier. Each member gets a dedicated
clinician (45-min 1:1 consults). Monthly members get unlimited human health coaching. Members get a
dashboard, 30% off its own supplement line, and prescriptions delivered to the door. All plans are
HSA/FSA eligible. No food logging or nutrition tooling was found.

**Advanced features.**
- **Lifescore:** a 0–100 composite of biomarkers, a questionnaire and clinician review, with biological
  age as one of its three parts. It is not described as a trained or validated model.
- **Rx pathways:** TRT (with PSA monitoring while on therapy), menopause management, GLP-1s
  (semaglutide/tirzepatide; BMI ≥30, or ≥27 with a comorbidity) and "select peptides" on the monthly tier.
- **Wearables:** claimed sync with Oura, WHOOP, Withings and Fitbit. One third-party review says it has no
  wearable integration, so treat it as shallow or unverified.
- **Not offered:** genomics, imaging, CGM, AI coach, disease/mortality prediction, safety/SOS and
  caregiver features. None were found.

**Pricing** (from the official landing pages, Oct 2026):
- Maintenance: $499/yr, 2 draws, no consults.
- Core Annual: $599/yr (listed at $699), 2 draws, 1 consult.
- Monthly: $199 first month, then $149/mo; 4 draws, 4 consults, unlimited coaching. A third-party site
  also lists a $1,449 annual option, which we have not verified.
- The ~$3,500/yr figure on a competitor's comparison page does not match the official plans. It probably
  includes therapy costs.

**Weaknesses.**
- Trustpilot and review-site complaints: upselling into prescriptions and supplements (one reviewer
  reported ~$500/mo on top of the membership), slow support, and trouble booking clinicians.
- Supplement sourcing and testing transparency was questioned by one reviewer.
- The peptide offering rests on thin human evidence and uncertain regulatory status.
- Insight between draws is thin: a 2–4×/yr snapshot with no continuous data layer.
- Its incentives (revenue from therapies and supplements) work against neutral advice.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. A **Lifescore-style composite score**: one 0–100 headline number over PhenoAge, our blood and muscle
     clocks, and our risk models. Unlike Lifescore, ours rests on trained, validated models, so we
     should publish how it is computed.
  2. **Therapy-safety monitoring protocols** in the doctor workspace: TRT → PSA/haematocrit/lipids;
     GLP-1 → lean-mass loss (our muscle clock), glucose and HR trend from wearables. Continuous
     between-draw monitoring is something Lifeforce structurally can't do.
- *Operational parity via partnership:*
  3. A human-coach layer (partner coaches working inside the centre/doctor roles) for users who want a
     person.
  4. An Rx pathway via a licensed telehealth/pharmacy partner. Keep supplements out, or keep them
     brand-neutral, so we don't take on the upsell conflict that is Lifeforce's most-cited complaint.
- *Our opening:* Lifeforce's weak spots are a narrow panel, no continuous data, no AI, an unvalidated
  score, an upsell reputation and US-only reach. Our pitch against it: neutral, model-grounded advice
  with continuous wearable monitoring, without prescriptions as the business model.

Sources:
- [Lifeforce plans](https://www.mylifeforce.com/landers/start-now)
- [Maintenance tier](https://www.mylifeforce.com/landers/maintenance-membership)
- [Membership/wearables](https://www.mylifeforce.com/landers/membership)
- [GLP-1 approach](https://www.mylifeforce.com/journal/glp-1-weight-loss)
- [Trustpilot](https://www.trustpilot.com/review/mylifeforce.com?page=2)
- [Superpower vs Lifeforce](https://superpower.com/biomarker-testing-companies/superpower-vs-lifeforce)
  (competitor-authored)
- [Crown Counseling comparison](https://crowncounseling.com/reviews/life-force-vs-function-health-vs-fountain-life)
- [dot.LA 2023](https://dot.la/lifeforce-tony-robbins-2660767290.html)
- [Series A](https://www.citybiz.co/?p=420190)
- [Mito Health comparison](https://mitohealth.com/alternate/mitohealth-vs-lifeforce) (competitor; pricing
  likely inflated)
