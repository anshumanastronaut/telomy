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

---

## 2026-10-21 — Bryan Johnson Blueprint / Immortals

Bryan Johnson's company now runs under the **Immortals** name. **Blueprint** is its consumer-products
brand (supplements, food, skincare, haircare, devices). The rest sits beside it: a biomarker
membership, an online Rx storefront (Immortals Medicine), a concierge tier and the free Immortals app
with "BryanAI". Secondary coverage reports a ~$60M round in late 2025, with Gyre Renwick as CEO and
Kate Tolo as co-founder. We have not checked that figure against an official announcement. Sources
disagree on the naming, so in this profile "Blueprint" means the whole company.

**Basic features.**
- **Biomarker membership:** 100+ biomarkers from blood and urine. There are two rounds a year, a
  baseline and a 6-month follow-up, drawn **in person at Quest Diagnostics labs**. There is no home
  collection.
- **Inconsistent marker counts:** the page gives "160+ measurements/yr", then "up to 226" (140 + 86),
  then "200+ lab tests".
- **Results and availability:** results arrive in about 1–2 weeks. The service is US-only and excludes
  AZ, HI, NJ, NY and RI.
- **Free Immortals app:** tracks supplements, nutrition, medications and biomarkers. It **accepts lab
  uploads from any provider for free** and syncs wearables. The listing names Apple Watch, Oura,
  WHOOP, Garmin, Fitbit, Google Fit, Eight Sleep and Strava, and the site adds Dexcom.
- **Not offered:** no human doctor consults beyond prescription clinician check-ins, no records vault
  beyond lab storage, and no food logging beyond tracking.

**Advanced features.**
- **Biological age:** a mail-in **DNA-methylation "Speed of Aging" kit** sold separately, using a
  "third-generation" clock. Its current price is unverified.
- **Organ age:** "Speed of Aging + Biological Organ Age" inside the biomarker platform is still
  marked **"coming soon"** (Oct 2026).
- **Immortals Medicine Rx (à la carte, no membership):** GLP-1s (semaglutide, tirzepatide,
  Wegovy/Zepbound), metformin, acarbose, SGLT2 drugs (Jardiance, Brenzavvy), estradiol, sermorelin,
  NAD+, PT-141, tadalafil, oral minoxidil and tretinoin. Each needs a clinician consult, and delivery
  takes about 3 days.
- **BryanAI chat:** builds "evidence-backed protocols" from your data. Nothing public describes
  grounding or validation.
- **Microplastics blood test:** $135.
- **Not offered:** no imaging, genomics/PGx, trained disease or mortality prediction, fall/SOS safety,
  or caregiver features.

**Pricing.**
- Biomarkers: $365/yr, the same price as Function Health and positioned directly against it. It is
  HSA/FSA-eligible via a Letter of Medical Necessity.
- Microplastics test: $135.
- Rx examples: tadalafil $24–40, acarbose $25–40, Brenzavvy $143–210.
- Immortals concierge: a $60k/yr "supported" tier and the $1M/yr full protocol (3 spots, Feb 2026,
  per TechCrunch).
- Full supplement stack: about $361/mo (per a Hone Health review).

**Weaknesses.**
- **Unreliable app:** recent App Store reviews are 1★ and say the app doesn't work and the chat is
  unusable. Google Play averages 3.6★ from only 5 reviews and reports crashes on launch. It is a small
  sample, but no positive expert review exists.
- **Commerce problems:** Trustpilot complaints describe lost or delayed shipments, slow support with
  no phone line, unwanted subscription billing and damaged product.
- **Thin evidence:** a third-party review found no clinical trials on the finished haircare products
  and undisclosed active concentrations.
- **Incentives:** revenue comes from supplements, food and Rx, so the advice has the same conflict of
  interest we flagged at Lifeforce.
- **Founder risk:** the brand is tied to Johnson's personal persona, and the press treats parts of it
  as spectacle.
- **Coverage gaps:** in-lab draws only, US-only with state exclusions, and organ age not yet shipped.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Per-organ biological age from standard bloods.** This is Blueprint's headline "coming soon"
     feature. We already train NHANES blood clocks, so liver, kidney, cardio-metabolic and immune
     sub-clocks from the same panel are a natural extension. We could ship them first, with published
     MAE.
  2. **Free bring-your-own-labs tier.** Free lab upload plus wearable sync is Blueprint's funnel.
     Telomy should parse any Indian lab PDF (Thyrocare, Dr Lal, SRL, Metropolis) into the Vault and
     run our clocks and risk models on it for free. Paid tiers would add fusion, the doctor workspace
     and the safety agent.
  3. **Reliability as a feature.** A grounded, on-device Telomy-LLX that works offline is a direct
     answer to BryanAI's "chat is unusable" reviews. We should state in the product what data each
     answer used.
- *Operational parity via partnership:*
  4. A methylation-clock lab partner, so users can optionally calibrate our blood clock against an
     epigenetic one. We should also look at Dexcom/Libre CGM ingestion, which both Blueprint and Oura
     now treat as standard.
- *Our opening:* Blueprint is a founder-led commerce brand with a $365 lab panel and a young, buggy
  AI app. It has no risk prediction, no safety layer, no clinical multi-role tooling and no presence
  in India. It competes on persona and products; we compete on validated models and neutral advice.

Sources:
- [Immortals biomarkers page](https://immortals.com/pages/biomarkers)
- [Immortals home (Rx, app)](https://immortals.com/)
- [Immortals app (App Store)](https://apps.apple.com/us/app/immortals-bryan-johnson/id6761206137)
- [Google Play](https://play.google.com/store/apps/details?id=com.bryanjohnson.immortals&hl=en)
- [TechCrunch, Feb 2026](https://techcrunch.com/2026/02/12/for-1-million-you-can-pay-bryan-johnson-or-bryanai-to-teach-you-how-to-live-longer/)
  (opinionated tone)
- [Athletech: $365 platform](https://athletechnews.com/bryan-johnson-joins-biomarker-testing-boom-with-365-platform-challenging-function-health/)
- [$60M round](https://longevity.technology/news/bryan-johnsons-blueprint-raises-star-studded-60m-funding-round/)
  (secondary)
- [Microplastics test](https://blueprint.bryanjohnson.com/products/microplastics-test)
- [Speed of Aging kit (Amazon)](https://www.amazon.com/Blueprint-Bryan-Johnson-Speed-Aging/dp/B0DNRD2BDG)
- [Trustpilot](https://www.trustpilot.com/review/blueprint.bryanjohnson.com)
- [Perfect Hair Health review](https://perfecthairhealth.com/blueprint-haircare-stack-product-review/)
- [Hone Health stack review](https://honehealth.com/edge/blueprint-stack-review/) (competitor-authored)

---

## 2026-10-21 — TruDiagnostic (Infinite Epigenetics)

TruDiagnostic is a CLIA-certified epigenetic lab in Lexington, Kentucky, founded in 2019. Its parent
company, **Infinite Epigenetics**, bought **Tally Health** (David Sinclair's cheek-swab TallyAge
brand) on 29 Apr 2026. Terms were not disclosed. Tally stays a separate consumer brand. The combined
company says it holds the largest private adult DNA-methylation dataset. That is its own claim.
TruDiagnostic is a lab first and an app second: most of what it sells is clocks, not care.

**Basic features.**
- **Sample:** an at-home finger-prick dried blood spot. There is no phlebotomy and no standard blood
  chemistry panel. It measures methylation only.
- **Products:** TruAge, described as "75+ epigenetic biomarkers" (biological age, pace of aging and
  11 organ ages). TruHealth, described as "105–110 epigenetic biomarkers" (nutrition, inflammation,
  metabolic and toxin proxies). A combined kit is sold as "180+ biomarkers". The counts differ
  between sections of the same site.
- **Results:** delivered through a web portal (portal.trudiagnostic.com). We found no mobile app.
  Results take about 3–4 weeks after the lab receives the sample, and some panels take 4–6 weeks.
- **Consult:** a 30-minute consultation that one 2026 review says has moved between "included" and
  "add-on" over time.
- **Not offered:** no wearable integration, no food logging, no doctor network for treatment, no
  Rx, no records vault and no e-pharmacy.
- **Availability:** free shipping is stated only for the continental US. There is a UK reseller
  (Lola Health, £380). We found **no evidence of availability in India**.

**Advanced features.**
- **Clock stack in one report:**
  - OMICmAge, built with Harvard and validated on more than 14k of TruDiagnostic's own samples.
  - DunedinPACE, a pace-of-aging measure licensed from Duke/Dunedin.
  - GrimAge principal-component inputs.
  - A telomere-length estimate.
  - About 20 immune-cell subsets deconvolved from methylation.
- **SYMPHONYAge organ ages:** covers 11 systems: lung, heart, brain, hormone, metabolic,
  musculoskeletal, blood, liver, inflammation, kidney and immune. It was developed at Yale and
  launched in June 2024. The launch claimed it beat existing clocks on 16 outcomes across 5,129
  samples, but at launch that validation was only a bioRxiv preprint. **This means organ age from
  methylation is already shipping**, while Blueprint's version is still "coming soon".
- **Report assistant:** a Q&A assistant appears in screenshots of the portal. Nothing is published
  about whether it is grounded in the user's data or validated.
- **Developer API:** a public v2 API reference exists. TruDiagnostic also does research and
  commercial (B2B) lab services.
- **Clinician channel:** a Provider Network and an affiliate program. It has been listed in the
  **Fullscript** labs catalog since Sep 2026 and is also on Rupa Health.
- **Not offered:** no trained disease or mortality risk model is sold to consumers ("death risk"
  appears only as a topic label), no PGx or variant genomics, no imaging, and no safety or
  caregiver features.

**Pricing.** These are 2026 prices from reviews, and the official page does not list them:
- TruAge COMPLETE: **$499** one-off, or about **$249 per test** with Subscribe & Save.
- TruAge + TruHealth: **$849**.
- TruAge PACE: about **$229** (DunedinPACE only, from one comparison site).
- UK: £380.
- The tests are HSA/FSA-eligible and are not covered by insurance.

**Weaknesses.**
- **Unproven usefulness:** reviews say the clocks have little proven clinical actionability and are
  not FDA-cleared. The tests are sold as research/wellness tools.
- **Little outcome evidence:** there is limited prospective evidence that the age outputs predict
  who gets disease. The critic who said this, Generation Lab, sells a competing test, so this point
  is not neutral.
- **Clocks disagree:** different algorithms give ages several years apart, so users get confused
  about which number to believe.
- **Slow turnaround:** 3–6 weeks per result. Some users report delays that were not explained
  (Nucleus review).
- **Price:** $499 is expensive for one number that depends on a lab, and a single retest shift is
  not proof that an intervention worked.
- **Thin product:** a web portal only, with no daily signal (no wearables), no plan to act on and
  no care pathway. Advice drifts toward supplements now that Tally is in the group.
- **Unverified claims:** the "Best test 2026" awards in Dec 2025–Jan 2026 are paid-style press
  releases, not independent evaluations. We should not cite them.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Organ-age clocks from routine bloods, priced at the cost of a standard panel.** TruDiagnostic
     proves people will pay $499 and wait a month for 11 organ ages from methylation. We can train
     per-system blood clocks on NHANES (liver, kidney, cardio-metabolic, immune/blood, hormone) from
     the same ₹1–2k panel users already get, and return them instantly. We should publish MAE and
     outcome associations, which answers the "preprint-only" weakness. This is now the
     highest-leverage model to build, because two rivals (TruDiagnostic shipped, Blueprint coming)
     have made it a category expectation.
  2. **A blood-based pace-of-aging metric.** DunedinPACE is TruDiagnostic's most-cited number. We
     can turn repeated blood-clock runs, plus wearable HRV and resting-HR trends between draws, into
     a continuous "pace" with a confidence interval. They cannot offer this: they have one sample
     every few months and no daily data.
  3. **Clock disagreement handled honestly.** Telomy-LLX should show uncertainty bands and explain
     why clocks diverge, grounded in the user's own values. TruDiagnostic's reviews cite this
     confusion as a pain point.
- *Operational parity via partnership:*
  4. **An optional methylation add-on through a lab partner.** Telomy stays the analysis and
     longitudinal layer, imports the methylation PDF/API results into the Vault, and calibrates our
     blood clocks against them. TruDiagnostic itself has a public API and a B2B services arm, which
     makes it a possible partner rather than only a rival. In India we would need a local
     methylation lab, since TruDiagnostic does not appear to ship there.
  5. **A practitioner ordering channel.** The Fullscript listing is how TruDiagnostic reaches
     clinicians. Our equivalent is the centre/doctor workspace plus listings with Indian lab
     aggregators and clinic chains.
- *Our opening:* TruDiagnostic has the best clock science of the consumer labs. But it sells one
  expensive, slow, US-centric snapshot with no daily data, no risk model, no care pathway and no
  app. Telomy can be the continuous, affordable, India-first layer that makes any clock (theirs or
  ours) actionable.

Sources:
- [TruDiagnostic home](https://www.trudiagnostic.com/) (products, finger-prick, portal, provider program; no prices)
- [SYMPHONYAge launch, PR Newswire, Jun 2024](https://www.prnewswire.com/news-releases/epigenetic-laboratory-trudiagnostic-launches-first-ever-organ-specific-aging-analysis-from-yale-developed-symphonyage-algorithms-302185301.html) (company release)
- [Infinite Epigenetics acquires Tally Health, BioSpace, Apr 2026](https://www.biospace.com/press-releases/infinite-epigenetics-acquires-tally-health-to-accelerate-the-future-of-epigenetics-driven-health-and-longevity)
- [GenomeWeb on the acquisition](https://www.genomeweb.com/business-news/infinite-epigenetics-acquires-tally-health)
- [Fullscript labs catalog listing](https://fullscript.com/blog/trudiagnostic-now-on-fullscript)
- [Rupa Health listing](https://www.rupahealth.com/lab-companies/trudiagnostic)
- [KnowYourDNA review](https://knowyourdna.com/trudiagnostic-review/) (prices verified May 2026; affiliate-style, and the authors had not tested the kit)
- [Lola Health (UK pricing)](https://lolahealth.com/blogs/longevity/truage-complete-vs-pace) (reseller)
- [Generation Lab critique](https://www.generationlab.com/blog/truage-epigenetic-test-review) (competitor-authored)
- [Nucleus review](https://mynucleus.com/blog/trudiagnostic-review) (competitor-authored)
- [Longevity Protocols SYMPHONY Age entry](https://longevity-protocols.com/en/knowledge-base/diagnostics/symphony-age-trudiagnostic/)
- [PR Newswire "Best Pace of Aging Test 2026"](https://www.prnewswire.com/news-releases/best-pace-of-aging-test-2026-trudiagnostic-recognized-for-dunedinpace-innovation-by-expert-consumers-302648665.html) (paid-style award; not evidence)

---

## 2026-10-21 — Tally Health

Tally Health is a New York consumer longevity brand co-founded by David Sinclair. It launched in
2023 with a $10M round. It has fewer than 20 remote staff, and its CEO is Melanie Goldey (Glossy,
Apr 2026). On 29 Apr 2026 **Infinite Epigenetics (TruDiagnostic's parent) acquired it**. Terms were
not disclosed. Tally stays a standalone brand with the "same core products" and gives a mostly-B2B
lab group a consumer channel. In practice it is **a cheek-swab clock used to sell a supplement
subscription**. No user or revenue figures are public.

**Basic features.**
- **Sample:** an at-home **cheek swab** that you mail back. It needs no blood and no phlebotomy, so
  it has the lowest friction of any clock we have profiled.
- **Result:** a single "TallyAge" biological age, delivered with **personalized Action Plans**
  (lifestyle advice) on a web/digital platform. Turnaround is about 3–6 weeks (sources vary).
- **Supplements:** a daily **Vitality** supplement is bundled into the membership. Reviews name its
  ingredients as Ca-AKG, quercetin, resveratrol, fisetin and spermidine; these are unverified on the
  label. Add-ons are sold separately (see Pricing).
- **Not offered:** no standard blood biomarkers, no wearable integration (the official membership
  page does not mention one), no doctor consults, no Rx, no records vault and no e-pharmacy.
  Shipping countries are not listed, and we found **no evidence of India availability**.

**Advanced features.**
- **CheekAge clock:**
  - It was trained on cheek methylation from more than 8,000 people and published in
    *GeroScience* (2023). That validation was run on public datasets (cancer, COVID-19, progeria).
  - In *Frontiers in Aging* (reported Oct 2024), co-authored with the University of Edinburgh,
    CheekAge was **significantly associated with mortality** in the Lothian Birth Cohorts (1,513
    people born 1921/1936; deaths from the NHS register). We found no hazard ratio in coverage. The
    study is company-co-authored, and we found no independent replication.
  - The number of sites is inconsistent: about 200k CpG sites per the paper coverage, while an
    affiliate review claims 850k.
- **Now inside the TruDiagnostic group:** after the acquisition, Tally will "have access to" the
  combined methylation dataset. Planned items are *more personalized* protocols and "dynamic health
  feedback". None of that has shipped as of Oct 2026.
- **Not offered:** no disease risk model, no organ ages (TruDiagnostic's SYMPHONYAge is blood-only,
  not cheek), no pace-of-aging metric surfaced to consumers, no genomics/PGx and no safety or
  caregiver features.

**Pricing** (2026 prices; the official page was checked 2026-10-21):
- Membership: **$129/mo**. It includes a TallyAge test **every 6 months**, Action Plans and daily
  Vitality. Older reviews cite quarterly tests and tiers up to $199/mo, which appear to be outdated.
- One-off test: **$249** (Glossy, Outliyr). Forbes and Biohacker Atlas list $229, and one site lists
  about $199, which is unverified.
- Add-ons per month: Amplify **$84**, Restore (sleep) **$79**, Sharpen **$74**, Defend **$74** and
  NAD+ **$59**.
- **Effective cost:** about $1,548/yr for 2 clock readings plus supplements. Most of what the money
  buys is the supplements.

**Weaknesses.**
- **Sample accuracy:** a cheek swab is noisier than blood for systemic aging. Oral bacteria and food
  residue add noise, and buccal cells are not the organs users care about. Critics, mostly rival
  sellers (Generation Lab, Nucleus, NOVOS), make this point, and the company has not published an
  accuracy figure for the consumer test.
- **Regulation and lab transparency:** the test is not FDA-cleared. The Nucleus review says the lab
  location and certification were not disclosed. This may have changed now that TruDiagnostic's CLIA
  lab is in the group, but we have not verified that.
- **Conflict of interest:** the test result drives the supplement upsell, and the action plans lead
  into the products. This is the same structural conflict we flagged for Blueprint and Lifeforce.
- **Thin signal:** the only data is one number every six months. There is no daily data, no blood
  chemistry and no clinician to act on it.
- **Little social proof:** Forbes noted very few customer reviews. A dietitian it quoted questioned
  whether a swab can measure biological age at all. Keep Health rates it 2/5 as "entry-level
  baseline only".

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **A no-needle entry tier.** Tally's real lesson is distribution: people will pay for a
     biological age if they do not need a blood draw. We can offer a **wearable + questionnaire
     "provisional age"** from ring/WHOOP HRV, resting HR, VO₂-max proxy, sleep and anthropometrics.
     It would come with an explicit uncertainty band, update daily, and convert users to a blood
     panel for the full clock. That gives us the swab's low friction with continuous data, which
     Tally cannot match.
  2. **Publish our validation.** Tally's main credibility asset is two peer-reviewed papers,
     including a mortality association. We already have internal MAE and 10-year-mortality numbers.
     We should write up the NHANES blood clock and the mortality model (preprint first, with
     C-index and hazard ratio per year of age gap) so that we can point to evidence rather than
     marketing.
- *Operational parity via partnership:*
  3. **A methylation add-on through the TruDiagnostic group.** We already noted their public API and
     B2B arm. Tally now gives that group a cheek-swab option, which ships more easily than a blood
     spot. If an India lab or import route can be arranged, Telomy could offer it as an import into
     the Vault with no supplement attached.
- *Our opening:* Tally sells one noisy number twice a year to fund a supplement subscription
  (about $1.5k/yr), with no blood data, no wearable data, no doctor and no India presence. Telomy
  can position as **"the clock with no upsell"**: continuous, explained by grounded on-device AI,
  linked to actual risk prediction, and priced for India.

Sources:
- [Tally Health membership (official, checked 2026-10-21)](https://tallyhealth.com/products/membership) ($129/mo, 6-monthly test, add-on prices)
- [Tally Health home](https://tallyhealth.com/)
- [Glossy, Apr 2026: Tally acquired by Infinite Epigenetics](https://www.glossy.co/beauty/wellness/tally-health-is-acquired-as-vertical-integration-and-biological-age-trends-in-wellness/) (staff, CEO, $249 test, post-deal plans)
- [Medical Device Network, Oct 2024: CheekAge mortality study](https://www.medicaldevice-network.com/news/tally-health-cheekage-swab-test-able-to-predict-user-mortality-through-dna/)
- [Tally CheekAge paper press release (Fitt Insider)](https://insider.fitt.co/press-release/tally-health-publishes-groundbreaking-scientific-paper-on-innovative-next-generation-epigenetic-age-clock/) (company release)
- [Longevity.Technology on the CheekAge clock](https://longevity.technology/news/tally-health-announces-innovative-next-gen-epigenetic-age-clock/)
- [Fast Company, 2023: $10M round](https://www.fastcompany.com/90876849/tally-health-anti-aging-test)
- [Forbes Health review](https://www.forbes.com/health/healthy-aging/tally-health-review/) (older pricing; few reviews; dietitian critique)
- [Nucleus review](https://mynucleus.com/blog/tally-health-reviews) (competitor-authored)
- [Generation Lab review](https://www.generationlab.com/blog/tally-health-reviews-david-sinclair) (competitor-authored)
- [NOVOS comparison](https://novoslabs.com/what-to-look-for-in-epigenetic-biological-age-tests-david-sinclairs-tallyage-vs-elysiums-index-vs-novos-age/) (competitor-authored)
- [Keep Health biological age tests](https://keep.health/biological-age-tests/) (2/5 rating)
- [Outliyr epigenetic tests 2026](https://outliyr.com/best-epigenetic-age-tests-review) (affiliate-style; 850k-site claim)
- [Biohacker Atlas review 2026](https://biohackeratlas.com/biological-age-testing/tally-health-tallyage/) (affiliate-style)

---

## 2026-10-21 — Elysium Health

Elysium Health is a New York supplement company founded in 2014 by MIT biologist Leonard Guarente
(now its Chief Scientist), Dan Alminana and Eric Marcotulli. Its last disclosed raise was a $20M
Series B in Dec 2016. The business is **supplements first**: Basis (NR + pterostilbene, 2015), then
Matter (brain), Format (immune), Mosaic (skin), Vision (eye), and in 2026 **Creatine+** (Jun) and
**Balance** (menopause; announced 15 Oct, on sale 18 Oct 2026). On top of that it sells one test,
**Index** (saliva epigenetic clock, 2019). In 2026 it moved into telehealth: **TELI, The Elysium
Longevity Institute**, was announced 28 May and opened 9 Sep 2026. No user or revenue figures are
public.

**Basic features.**
- **Sample:** an at-home **saliva** kit that you mail back. Results arrive in about 6 weeks
  (official page: DNA extraction, methylation profiling, then calculation).
- **Results:** delivered through a web dashboard (my.elysiumhealth.com). The product page shows an
  age-tracking app, but its features are not described.
- **Recommendations:** "100+ science-based lifestyle recommendations" come with the result. They
  are static; there is no coach, human or AI.
- **Consults (TELI only):** a medical intake reviewed by a licensed provider, then portal messaging
  with a reply "typically within one business day". TELI is US-only, for adults in states where it
  operates. The list of states is not published.
- **Not offered:** no blood biomarker panel, no wearable integration, no nutrition logging, no
  records vault and no e-pharmacy beyond TELI's own compounded and branded drugs. International
  sales go through iHerb and a Canada site; we found **no India-specific presence**.

**Advanced features.**
- **Index clock:**
  - It runs on the "APEX" platform, using a custom methylation chip built with Illumina. The
    approach was developed with Yale's Morgan Levine, an Elysium advisor.
  - It reports **overall biological age, a cumulative rate (pace) of aging, and 9 system ages**:
    brain, heart, metabolic, immune, inflammation, kidney, liver, hormone and blood.
  - The science behind it is Levine's **Systems Age** (Sehgal et al., *Nature Aging*, Sep 2025;
    11 systems; system scores predicted system-specific outcomes better than single global
    clocks). That paper is a **blood** methylation study. We found no published validation that
    the 9 saliva system ages carry the same predictive power. Elysium's "most precise and
    reliable" and "under a year of test-to-test noise" claims are company claims.
  - TruDiagnostic's SYMPHONYAge (profiled earlier) appears to come from the same Levine lineage.
    Two rivals therefore sell organ ages on similar science, one from blood and one from saliva.
- **TELI Rx (opened Sep 2026):** 17 protocols are listed on its site; the press release says 18.
  - *Weight management:* GLP-1s — Wegovy injection from $580/mo, Wegovy pill from $500, Zepbound
    $750, Ozempic from $780, Mounjaro $1,620, and Foundayo (orforglipron) $675.
  - *Cellular health:* metformin $30, low-dose naltrexone $35, NAD+ injection from $155 or nasal
    $145, glutathione, MICC-B12 and Lipo+ B6.
  - *Peptides:* sermorelin (injection or lozenge) and GHK-Cu cream.
  - The CMO is Omar Baker, MD, formerly Deputy CMO at UnitedHealth Group. The site does **not**
    say how Index or any lab result feeds protocol choice, and lists no lab requirement.
- **Research hook:** Index buyers get free enrollment in the Aging Research Center's TIME-A study.
  That gives Elysium a longitudinal cohort built from its own customers.
- **Not offered:** no disease or mortality risk model, no genomics/PGx, no CGM, no imaging, no
  safety and no caregiver features.

**Pricing** (official pages, checked 2026-10-21):
- **Index:** **$299** per kit. No subscription is listed. Older reviews cite $499, which is now
  outdated.
- **Basis:** **$65/mo** one-time purchase. Subscription and prepaid annual discounts exist, but the
  page shows no figure.
- **TELI:** priced per protocol, about $30–1,620/mo (above). No membership fee is shown.
- **Effective cost:** one review put Index + Basis + Matter at over $800/yr, before retests (older
  pricing). Not verified.

**Weaknesses.**
- **Saliva vs. the blood evidence:** the organ ages are sold from saliva, while the peer-reviewed
  work is on blood. In a 2023 MIT Technology Review piece, Elysium's own team said the test leaves
  out many factors known to affect aging, and the reviewer got a brain age at odds with his overall
  age. A Substack commenter cites a re-run sample with deviating results; this is unverified.
- **Not FDA-reviewed:** Index is explicitly "not a medical device".
- **Conflict of interest:** Elysium makes its money on supplements and now on Rx. The test, the
  recommendations and TELI all lead into its own products, the same conflict we flagged for
  Blueprint, Lifeforce and Tally.
- **Supplement evidence is thin:** Basis's flagship claim, roughly 40% higher NAD+ vs placebo
  (Dellinger trial), is about a biomarker, not an outcome. Matter rests on one Oxford trial of 168
  people over 70. Balance's evidence is an open-label Basis pilot plus S-equol data, which an
  independent review called preliminary.
- **Disconnected stack:** test, supplements and TELI sit side by side with **no wearable data, no
  blood panel and no visible loop from result to protocol to retest**. There is no AI coach.
- **Legal history:** years of litigation with ChromaDex/Dartmouth. Elysium largely won: the NR
  patents were held invalid (Fed. Cir., Feb 2023) and a jury verdict leaned its way. The cases show
  a supply-chain fight over its core ingredient rather than a current risk. We found no 2025–26
  case news.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Per-organ ages from routine bloods.** Elysium and TruDiagnostic both now sell 9–11 "system
     ages", so organ ages are becoming a **basic** expectation for a clock. Telomy can compute
     liver, kidney, cardio-metabolic, immune/inflammation and blood ages from a standard Indian
     blood panel. That needs no methylation lab. We would train them on NHANES in the same
     research/ageclock pipeline and report each with its error bar. This turns our "Organ-specific
     biological age" GAP into a feature rivals charge $299–499 for.
  2. **Close the loop that Elysium leaves open.** The plan would be: result, then a structured plan
     from Telomy-LLX grounded in that result, then wearable trend, then retest, then a re-scored
     risk. Every recommendation would be tied to the marker that motivated it. This is the honest
     contrast to "100+ static recommendations".
  3. **Women's-health layer.** Elysium is launching a menopause supplement, and Lifeforce sells
     menopause HRT. We could add sex-specific risk calibration and menopause-aware ring metrics
     (temperature, sleep, HRV). This is new: see the "Women's health" row in the matrix.
- *Operational parity via partnership:*
  4. **Rx and consent-based research.** TELI shows a supplement brand can add a GLP-1/metformin
     telehealth arm in about 4 months. In India the analogue is a partner tele-clinic and pharmacy
     on our doctor/centre workspaces. We would not build it ourselves. Separately, a TIME-A-style
     **opt-in research cohort** inside the app would give us the longitudinal data we need to
     publish our clocks.
- *Our opening:* Elysium sells a saliva clock whose organ-level claims rest on blood science. It
  sells it to fund supplements and now US-only prescriptions, with no daily data, no risk
  prediction and no India footprint. Telomy can offer organ ages from the blood test Indians
  already get, plus continuous wearables and a grounded explanation, with nothing to sell on top.

Sources:
- [Elysium Index product page (official, checked 2026-10-21)](https://www.elysiumhealth.com/products/index) ($299, saliva, 9 systems, APEX, ~6 weeks, TIME-A study)
- [Elysium Basis product page (official)](https://www.elysiumhealth.com/products/basis) ($65/mo, 40% NAD+ claim)
- [TELI site (official)](https://elysiumhealthrx.com/) (protocols and prices, portal messaging)
- [PR Newswire, 9 Sep 2026: TELI officially opens](https://www.prnewswire.com/news-releases/elysium-health-officially-opens-the-elysium-longevity-institute-teli-establishing-a-new-standard-for-longevity-medicine-302873132.html) (CMO Omar Baker, 18 protocols)
- [PR Newswire, 28 May 2026: TELI announced](https://www.prnewswire.com/news-releases/elysium-health-announces-the-launch-of-the-elysium-longevity-institute-teli-302783990.html)
- [PR Newswire, Oct 2026: Balance launch](https://www.prnewswire.com/news-releases/elysium-health-announces-the-launch-of-balance-a-first-of-its-kind-approach-to-perimenopause-and-menopause-support-grounded-in-longevity-science-302910000.html)
- [Nutritional Outlook: Creatine+](https://www.nutritionaloutlook.com/view/elysium-health-creatine-longevity-system)
- [NutraIngredients, 2 Sep 2026: supplements becoming one layer of longevity platforms](https://www.nutraingredients.com/Article/2026/09/02/healthspan-supplement-launches-enter-stacked-market-building-on-platforms/)
- Sehgal et al., Systems Age, Nature Aging 2025 (doi 10.1038/s43587-025-00958-3, PMID 40954326; final text not read): [PubMed preprint record](https://pubmed.ncbi.nlm.nih.gov/37503069/) and [bioRxiv preprint](https://www.biorxiv.org/content/10.1101/2023.07.13.548904.full.pdf)
- [Wikipedia: Elysium Health](https://en.wikipedia.org/wiki/Elysium_Health) (founding, products, litigation)
- [Justia: ChromaDex v. Elysium, Fed. Cir. 2023](https://law.justia.com/cases/federal/appellate-courts/cafc/22-1116/22-1116-2023-02-13.html)
- [SupplySide: jury verdict tilts toward Elysium](https://www.supplysidesj.com/supplements/jury-verdict-tilts-toward-elysium-health-in-dispute-with-chromadex-court-records-show)
- [MIT Technology Review, Apr 2023: "my brain and liver are older"](https://www.technologyreview.com/2023/04/14/1071610/brain-and-liver-are-older-than-they-should-be/)
- [Optimize Biomarkers Index review 2026](https://optimizebiomarkers.com/longevity-providers/elysium-health) (affiliate-style; $299 verified Aug 2026)
- [GlycanAge: Index review](https://glycanage.com/blog/lifestyle/elysium-index-age-test-review) and [TruAge vs Elysium](https://glycanage.com/blog/lifestyle/truage-vs-elysium-index-review) (competitor-authored)
- [Generation Lab: Elysium review](https://www.generationlab.com/blog/elysium-biological-age-test-review) (competitor-authored)
- [Nebula: Elysium review (2022)](https://nebula.org/blog/elysium-health-review/) (older pricing; $800+/yr estimate)

---

## 2026-10-21 — Thorne

Thorne is a US supplement maker, founded in 1984 and based in Summerville, South Carolina. It makes
its own products and sells them to consumers and through practitioners. In 2021 it merged with the
AI-testing startup Onegevity to form Thorne HealthTech, and it IPO'd that year. L Catterton took it
private for about $680M in 2023. On **4 Aug 2026 P&G agreed to buy it for about $3.8B in cash**. The
deal was expected to close later in 2026; we found no closing or antitrust news as of 21 Oct.
Revenue passed $500M in 2025, and CNBC (as cited by trade press) reported a pace of about $650M for
2026. Its Chief Science Officer is Nathan Price, a systems biologist and co-founder of Arivale.
**Main finding:** Thorne has **left the testing business it built**. In March 2026 it said it was
winding down its at-home kits, and test activation and lab requisitions ended **1 Jun 2026**. It
promised its own "biomarker insights" product as a limited beta later in 2026. Its focus is now
supplements plus an AI shopping advisor.

**Basic features.**
- **Supplements:** this is the core business. Thorne has a long-standing NSF Certified for Sport
  line; we did not re-verify that for 2026. It sells through its own site, Amazon and Fullscript,
  where it has been listed since 2022 for practitioner ordering.
- **Practitioner channel:** practitioner accounts and dispensing. Trade press describes "tens of
  thousands of practitioners" and 7M+ consumers. These are company figures, not verified.
- **Health tests (retired):** at-home kits for gut, sleep, stress, biological age, and earlier
  vitamin D, heart, weight, testosterone, menopause, fertility and thyroid. Blood panels (Essential
  ~$390 / Advanced ~$830) were offered, as was a "Health Insights" beta built with Lifeforce that
  analysed 50+ biomarkers. Prices come from a 2024 source and are now moot. The thorne.com tests
  page now only says it is "evolving our personal health testing experience" and asks visitors to
  sign up for updates.
- **Not offered:** no wearable integration, no consults or telehealth, no records vault, no
  nutrition logging, no CGM, no Rx pathway. India access appears to be imports and resellers only
  (not verified).

**Advanced features.**
- **Taia, an AI wellness advisor**, launched in Jan 2026 and sits on the homepage. It was built
  in-house under Price, using Thorne's internal knowledge base plus "foundational AI knowledge"; the
  LLM vendor is not disclosed. It answers questions about sleep, stress, energy, digestion and
  immunity, then recommends supplements and lifestyle changes. It does **not** use the user's labs
  or wearable data, it "does not diagnose or replace medical care", and it does not handle
  checkout. Company-reported numbers for the first six months: 200k+ messages, 350k+
  recommendations, a 94% like rate, and **about 8% higher average order value** than browsers.
  That last comparison is likely selection-biased and has not been verified.
- **Onegevity legacy:** Onegevity's algorithm powered the retired Biological Age Test and the gut
  test (Gutbio). No current biological-age product exists.
- **Not offered:** no risk prediction, no imaging, no genomics/PGx product, no safety and no
  caregiver features.

**Pricing.**
- Only supplements are sold now, priced per product. Subscribe-and-save and practitioner pricing
  exist.
- No test or membership pricing exists today. The beta has no announced price.
- Old test prices in reviews ($57–499 for the bio-age test, $198–399 for the gut test) conflict with
  each other and are outdated.

**Weaknesses.**
- **The testing retreat shows that mail-in kits sold standalone did not hold up.** Kits sold to
  drive supplement sales were shut down after about 7 years, just before the P&G sale. The cause was
  not disclosed, and we are inferring the economics. The "biomarker insights" replacement was
  unlaunched or unannounced at the time of writing.
- **The AI is a sales assistant, not a health model.** Taia is judged on average order value, and it
  cannot see any of the user's data. It is ungrounded in the person's own numbers, which is the same
  gap we flagged at Function and Lifeforce.
- **Conflict of interest:** every recommendation leads to a Thorne SKU. Under P&G this becomes a
  consumer-goods brand play, and Thorne's "practitioner-grade" credibility could suffer if
  practitioners see it as mass-market.
- **Integration uncertainty:** the P&G deal is pending, and product priorities may change after it
  closes.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **A grounded, personal advisor is the leapfrog over Taia.** Thorne's own CSO argues that AI
     wellness chatbots will be "table stakes" for the category. Taia proves people use them (200k
     messages in 6 months) but answers from a catalogue, not the user. Telomy-LLX already
     tool-calls the user's own biomarkers, clocks and wearable trends. We should make that visible:
     every answer should show which of *your* values it used. We should track a quality metric
     (grounding accuracy, refusal correctness), not average order value.
  2. **Don't ship standalone kits; ship a loop.** Thorne's exit is evidence that one-off mail-in
     tests churn. Telomy's test touchpoint should always come with continuous wearables, a plan
     and a scheduled retest (our "Retest subscription cadence" row). Then the blood draw is one
     step in a loop, not the product itself.
- *Operational parity via partnership:*
  3. **A practitioner channel, without selling supplements.** Thorne's strongest asset was
     practitioner distribution (Fullscript). In India the analogue is listing Telomy reports and
     clocks with clinic chains and lab aggregators, using our doctor and centre workspaces as the
     practitioner tooling. A practitioner may recommend any brand, and Telomy takes no product
     margin.
- *Our opening:* the best-funded supplement brand in the category is buying its way into consumer
  goods (P&G) and stepping back from diagnostics. That leaves "science-backed personal health" with
  fewer serious players, especially outside the US, where Thorne never ran tests. A neutral
  platform with no product conflict, grounded in the user's own data, is the contrast.

Sources:
- [Athletech News, 5 Mar 2026: Thorne scraps at-home kits, plans biomarker testing](https://athletechnews.com/thorne-scraps-at-home-kits-plans-biomarker-testing/)
- [Thorne tests page (official, checked 2026-10-21)](https://www.thorne.com/tests) ("evolving our personal health testing experience")
- [Thorne FAQ: tests](https://www.thorne.com/faqs/tests) (1 Jun activation deadline, per secondary reporting; not re-read)
- [NutraIngredients, 4 Aug 2026: P&G to acquire Thorne](https://www.nutraingredients.com/Article/2026/08/04/pg-to-acquire-thorne-in-premium-wellness-play/)
- [Nutritional Outlook: P&G to acquire Thorne for $3.8B](https://nutritionaloutlook.com/view/procter-gamble-to-acquire-thorne-f3-8-billion)
- [Jones Day deal note](https://www.jonesday.com/en/practices/experience/2026/08/the-procter-amp-gamble-company-acquires-thorne-from-l-catterton-for-38-billion)
- [Quartz: Unilever explored ~$4B bid](https://qz.com/unilever-bid-thorne-supplements-4-billion-062626)
- [Glossy, 2 Apr 2026: Nathan Price on AI chatbots as "table stakes"](https://www.glossy.co/beauty/why-ai-powered-wellness-chatbots-will-be-table-stakes-for-supplement-brands-with-thorne-cso-dr-nathan-price/) (Taia metrics, 8% AOV)
- [Glossy: How Thorne is leveraging an AI wellness advisor](https://www.glossy.co/beauty/wellness/how-thorne-is-leveraging-an-ai-powered-wellness-advisor-chatbot-in-the-chatgpt-era/)
- [NutraIngredients, 12 Jan 2026: AI wellness advisors, Thorne](https://www.nutraingredients.com/Article/2026/01/12/are-ai-powered-wellness-advisors-the-future-of-personalized-nutrition-thorne-thinks-so/) ("does not diagnose or replace medical care")
- [Stock Titan: Fullscript adds Thorne (2022)](https://www.stocktitan.net/news/THRN/fullscript-adds-thorne-health-tech-to-comprehensive-product-na0naw63br7o.html)
- [Thorne HealthTech S-1 (2021)](https://www.sec.gov/Archives/edgar/data/1844280/000119312521217566/d162335ds1.htm) and [LinkedIn: Thorne + Onegevity merge](https://www.linkedin.com/pulse/we-thorne-healthtech-onegevity-merge-creating-new-parent-jacobson)
- [Flore vs Thorne (competitor-authored)](https://flore.com/pages/vs-thorne), [Outliyr bio-age test review 2026](https://outliyr.com/best-biological-age-tests) (affiliate-style, likely predates the wind-down)

---

## 2026-10-22 — Zoe

ZOE is a UK personalised-nutrition company, co-founded by Prof Tim Spector, Jonathan Wolf and George
Hadjigeorgiou. Its science base is the PREDICT cohort studies: thousands of people wore CGMs and had
blood-fat tests after standard meals.
**Main finding:** ZOE has **dropped the measured metabolic side of its product.** It no longer ships
CGMs or blood-fat tests. Instead it predicts glucose and blood-fat responses from a questionnaire,
and the only thing it still measures is an optional £149 stool microbiome test. Its finances are
shrinking:
- In the year to Aug 2025, revenue roughly halved (£66.1m → £34.1m).
- Membership revenue fell from £27.7m to £17.4m.
- Losses passed £20m, close to double the prior year.
- It cut a further 139 jobs.

These figures come from Companies House filings as reported by The Grocer on 29 Apr 2026. Its CFO
called the revenue drop a "one-off strategic move" toward affordability. ZOE raised £5m+ in an
Oct 2025 crowdfund (£1m target), launched its app in the US in May 2025, and plans to expand into
Europe.

**Basic features.**
- **Food logging:** by photo, text description or barcode. The app keeps daily tallies of macros,
  fibre, calories and the number of different plants eaten.
- **ZOE score (0–100) for each food and meal:** foods are banded from "enjoy occasionally" to
  "enjoy daily".
- **Processed Food Risk Scale** for packaged foods, with five levels. It is based on energy
  density, how fast the food can be eaten, hyperpalatability and additives.
- **"Ziggie" coach:** an in-app coach with streaks, habits and nutrition-science lessons, plus food
  swap suggestions.
- **Free entry:** the app is free in the US, and you can start without any test.
- **Products:** the Daily30+ plant supplement and, since Jun 2026, a Gut Health Bar.
- **Not offered:** no records vault, no doctor consults, no lab panel, no e-pharmacy, and no
  wearable integration (none is listed on the App Store page or the ZOE 2.0 page).

**Advanced features.**
- **Gut microbiome test:** sequenced from a stool sample. Since ZOE 2.0 (Mar 2026) it reports a
  score out of 1,000 and "gut clusters", and it recommends foods that feed beneficial microbes. ZOE
  says it has sequenced 300k+ microbiomes, against a goal of 1M.
- **Predicted glucose and blood-fat response:** ZOE says its proprietary model, trained on
  PREDICT plus its microbiome data, removes the need for "cookies, a blood sample, or a CGM". **We
  found no published accuracy figures** for this sensor-free prediction. The original PREDICT
  research itself found CGM readings unreliable for classifying individual meal responses
  (Am J Clin Nutr 2022, 394 people wearing two CGMs each).
- **Research output:** a strong publication record from PREDICT. A Jul 2026 company study found
  that plant diversity beat probiotics for gut health (company-run study).
- **Not offered:** no biological-age score, no disease or mortality risk, no imaging, no
  genomics, no Rx pathway, no safety or caregiver features.

**Pricing.**
- **UK:** £149 one-off gut test, plus membership from £9.99/mo. That price was cut 60% from £24.99
  in 2025. The old kit with CGM and blood tests cost £299.99.
- **US:** free app. ZOE Premium costs $99.99/yr or $15.99/mo on the App Store. Third-party US
  guides quoting $24.99–59.99/mo look outdated.
- **Daily30+:** sold as a separate subscription.

**Weaknesses.**
- **Its metabolic claims now rest on an unverified model.** Removing the CGM made the product
  cheaper but less personal, and the accuracy of the replacement model is not public.
- **Shrinking business:** revenue roughly halved, losses deepened and staff were cut. Growth now
  leans on supplements and snack bars, which is a product conflict like Thorne's and Elysium's.
- **Regulatory credibility:** the ASA ruled a Daily30+ ad misleading because it called the product
  a "wholefood supplement" free of ultra-processed ingredients. ZOE appealed, and the ruling was
  upheld in Mar 2026; Spector called it "pedantry". It is an awkward look for a brand built on
  attacking ultra-processed food.
- **App quality and trust:**
  - App Store and Trustpilot users report foods being misidentified and homemade recipes being
    tedious to log.
  - Users say the 2026 redesign removed features.
  - The AI coach is described as repetitive.
  - The most common complaint is billing: renewals with no reminder, and an app subscription and
    supplement subscription that cancel separately.
- **Narrow scope:** nutrition only. There is no blood work, no wearables, no clinical layer, and no
  India presence.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **A personalised glucose-response model built on measured data.** ZOE gave up measurement for
     price. We already estimate glycaemic load per meal in `food.py`. The leapfrog is a personal
     response model that learns from the user's own bloods (HbA1c, fasting glucose, TG/HDL), their
     wearable data (sleep, HRV, activity before meals) and, when available, a short CGM period. We
     should publish its error against CGM ground truth, which ZOE has not done for its version.
  2. **ZOE-parity food-quality features that cost us little:** an in-app barcode scanner on top of
     our existing NOVA + Nutri-Score model trained on Open Food Facts, and a weekly plant-diversity
     count taken from logged foods. The IFCT food database gives the Indian dishes and plants that
     ZOE's Western database lacks.
  3. **Grounded coach, not a repetitive one:** Telomy-LLX should explain every meal score using
     the user's own numbers ("this raised your predicted glucose because your HbA1c is 6.1 and you
     slept 5 h"). That directly answers the "Ziggie repeats itself" complaint.
- *Operational parity via partnership:*
  4. **Microbiome testing only through a lab partner, and only later.** ZOE's own retreat to a
     microbiome-only kit suggests a stool test alone does not hold users. If we add one, it should
     feed the risk engine, not be sold as a standalone product.
- *Our opening:* ZOE proved there is mass demand for "is this food good for *me*?" (300k+ tests),
  then cut out the measured personalisation to survive. Telomy can own personalised nutrition built
  on measured data: bloods + wearables + photo logging, with Indian cuisine, honest billing and no
  supplement upsell.

Sources:
- [The Grocer, 29 Apr 2026: Zoe losses swell as it cuts membership price](https://www.thegrocer.co.uk/news/zoe-gut-health-app-losses-swell-as-it-slashes-membership-price/718306.article) (Companies House figures, CGM/blood-fat dropped, US launch May 2025)
- [ZOE: ZOE 2.0, science made simple (official, updated 17 Mar 2026)](https://zoe.com/learn/zoe-2-0-science-made-simple)
- [ZOE: How it works (official)](https://zoe.com/how-it-works) (sensor-free prediction claim, 300k profiles)
- [App Store: ZOE Health, AI Meal Tracker](https://apps.apple.com/us/app/zoe-health-ai-meal-tracker/id1471632228) (Premium $99.99/$15.99, 4.8★ from 7.1k ratings, reviews)
- [NutraIngredients, 11 Mar 2026: Zoe fails to overturn ASA ruling](https://www.nutraingredients.com/Article/2026/03/11/zoe-fails-to-overturn-asa-ruling-on-gut-supplement-ad/), [Marketing Week: Zoe "stunned"](https://www.marketingweek.com/zoe-stunned-asa-ad-ban/)
- [NutraIngredients, 16 Jul 2026: plant diversity vs probiotics study](https://www.nutraingredients.com/Article/2026/07/16/zoe-study-plant-diversity-beats-probiotics-for-gut-health/), [NutraIngredients, 25 Jun 2026: Gut Health Bar](https://www.nutraingredients.com/Article/2026/06/25/zoe-targets-fiber-gap-with-new-gut-health-bar/)
- [Am J Clin Nutr 2022: CGM validity for categorising glycaemic responses (PREDICT)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9170468/)
- [Trustpilot: ZOE reviews](https://uk.trustpilot.com/review/zoe.com) (billing and AI-coach complaints; self-selected sample)
- [Which? Zoe review](https://www.which.co.uk/reviews/nutrition-and-supplements/article/zoe-review-is-it-worth-it-aOVeL1R5BW52), [NutriScan: Is ZOE free? (Sep 2026, competitor-authored)](https://nutriscan.app/blog/posts/is-zoe-free-2026-zoe-pricing-0e51cc923e)

---

## 2026-10-22 — Levels

Levels (Levels Health Inc., US; co-founder and CEO Sam Corcos) made the "CGM for people without
diabetes" category popular. It says it has served 60k+ members (company figure, 2024). Funding is
roughly $67–80M across rounds, including community crowdfunding; the last round found was a $10M
Series A extension in Aug 2024 (a16z, Long Journey). We found no 2025–26 funding or layoff news.
**Main finding:** like ZOE, **Levels has unbundled the sensor.** The entry product is now a
$15/mo software subscription. The CGM (Dexcom Stelo) and lab panels are optional add-ons, and the
old $199/mo CGM bundle is a legacy plan. At the same time, Dexcom's own Stelo app has added AI
photo meal logging, a food database and an AI coach (2025–26). That squeezes any app whose main
value is "a nicer screen on top of one sensor".

**Basic features.**
- **Food + exercise logging** with glucose correlation, meal comparison and daily reports.
- **Zone Score / glucose-stability score**, plus challenges.
- **Adaptive programs:** glucose stability, heart health, weight loss.
- **Apple Health import:** sleep, steps, heart rate, weight. No specific wearable brands are listed
  on the official page.
- **Unlimited uploads of past bloodwork and health documents**, even in the base tier.
- **Labs:** Basic panel 28 markers $99 (cardiovascular, metabolic, kidney, liver). Comprehensive
  panel 110+ markers $399 (adds blood counts, hormones, nutrients, cortisol, urinalysis). The panels
  are labelled "Levels Labs – Quest". The support page does not say whether home collection is
  offered.
- **Not offered:** no records vault beyond uploads, no consult on demand, no e-pharmacy, no Rx
  pathway (no GLP-1 program on the official page as of Oct 2026).

**Advanced features.**
- **CGM-derived insights:** glucose curves per meal and A/B comparison of food swaps. Reviewers say
  sensors are Dexcom-only (Stelo or G7); that claim is third-party, not on the official page.
- **Clinician review of data twice a year** in Core/Complete. This is a review, not a consult.
- **Levels Pro:** a practitioner dashboard with a patient roster, live metrics and engagement
  signals. Levels claims its AI pre-visit summaries cut prep from 30 to 5 minutes (company claim,
  unverified). Its own blog coaches clinics to price CGM programs at $99–299/mo or $1,200–2,400 per
  12 weeks.
- **Research:** an ongoing observational glucose study in people without diabetes.
- **Not offered:** no biological-age score, no disease or mortality risk model, no imaging,
  genomics, safety or caregiver features. The AI is "AI health insights / habit tracking"; there is
  no sign it is grounded in a model of the user's risk.

**Pricing (official homepage, Oct 2026; all HSA/FSA eligible).**
- **Build your system:** $15/mo or $80/yr. App, food logging, AI insights, programs, wearable
  import, bloodwork upload. No CGM or labs.
- **Core:** $399/yr. 2 Essential panels (28+ markers), 1 month of CGM, clinician review 2x/yr.
- **Complete:** $1,329/yr. 2 Comprehensive panels (100+ markers), 2 months of CGM, one 50-min
  functional-nutritionist session, concierge support.
- **Add-ons:** Stelo shipment about $89 (third-party check, Sep 2026), panels $99 / $399.
- **Legacy:** Core $499/yr and Complete $1,999/yr. Many 2026 review blogs still quote $199/mo; that
  figure is out of date.

**Weaknesses.**
- **Its moat is eroding.** Dexcom now ships photo logging and AI insights in Stelo itself, and an
  OTC sensor plus the free Dexcom app covers much of Levels' base value.
- **The CGM is only used briefly.** Core includes one month of sensor per year, so most of the year
  the "metabolic" product runs on logging alone.
- **Little human help.** The base tier has no coaching and Complete has one nutritionist session.
  Review blogs (affiliate-style, low trust) list cost, lack of human coaching and sensor adhesion as
  the top complaints.
- **App quality.** It is rated 4.7★ from 6.7k ratings, but recent App Store reviews report sync
  failures, educational articles disappearing, generic insights for common foods, and a Mar 2026
  report of the AI coach giving wrong advice and misreading time periods.
- **Narrow, glucose-centric view.** There is no risk prediction, no clinical action pathway, and
  no presence outside the US.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Sensor-agnostic glucose ingestion** from HealthKit / Health Connect (Stelo, Libre and
     Ultrahuman M1 all write there). This puts measured CGM curves into our existing food + fusion
     engine without a sensor partnership. It also enables Levels-style meal A/B comparison and lets
     us calibrate the glycaemic-load model in `food.py` against real curves. That is the
     personalised-response leapfrog noted in the ZOE profile.
  2. **Glucose that stays useful between sensor periods.** Train a per-user response model during a
     2–4 week CGM period, then keep predicting from bloods + wearables + photo-logged meals after
     the sensor comes off. That fixes Levels' "one month a year" gap.
  3. **Doctor-side remote-program view.** Our doctor workspace already exists. Add a patient roster
     with glucose/HRV/adherence flags and a Telomy-LLX pre-visit summary grounded in the patient's
     own numbers, to match Levels Pro. The clinics, nutritionists and HBOT/longevity centres that
     use our centre workspace are the buyers.
- *Operational parity via partnership:*
  4. **A CGM bundle through an Indian supplier** (Libre is widely sold OTC in India; Ultrahuman M1 is
     local), priced as a short add-on rather than a subscription, plus partner labs for a Basic
     (~28 marker) and Comprehensive panel.
- *Our opening:* Levels and ZOE are both retreating from bundled sensors to cheap software, while
  Dexcom builds the software itself. The defensible position is **not** "best CGM app". It is the
  layer that fuses glucose with bloods, wearables, meals and risk models, and that a clinician can
  act on. Levels has no risk model and no Rx/clinical pathway, and Telomy has both the risk engine
  and the multi-role clinical OS.

Sources:
- [Levels homepage (official, © 2026): tiers, prices, inclusions](https://www.levels.com/)
- [Levels Support: Basic vs Comprehensive Panel (updated 27 Feb 2026)](https://support.levels.com/article/563-basic-vs-comprehensive-panel)
- [App Store: Levels – Metabolic Health](https://apps.apple.com/us/app/levels-metabolic-health/id1481511675) (4.7★/6.7k, $15/$80 IAP, reviews)
- [Levels blog: How clinics package and price CGM programs](https://www.levels.com/blog/cgm-program-pricing-clinic-adoption), [Levels Pro: practitioner CGM dashboard guide](https://www.levels.com/pro/guides/practitioner-cgm-dashboard) (vendor marketing)
- [Health3 vs Levels (competitor-authored, checked 6 Sep 2026)](https://www.health3.app/compare/health3-vs-levels/) (Stelo add-on price, legacy plans)
- [Wareable: Dexcom Stelo AI app overhaul](https://www.wareable.com/health-and-wellbeing/dexcom-stelo-cgm-pediatric-fda-clearance-new-ai-metabolic-meal-logging), [Citeline: Dexcom rebuilds Stelo, takes it global](https://insights.citeline.com/medtech-insight/device-area/diabetic-care/ai-coach-meal-photos-dexcom-rebuilds-stelo-from-the-ground-up-takes-it-global-K4ZA4OBFNZGN3JHCOS2OIJIJ3Q/)
- [Fitt Insider: Levels $10M Series A extension (2024)](https://insider.fitt.co/press-release/levels-raises-10m-series-a-extension-from-community-long-journey-and-a16z-to-fund-more-accessible-metabolic-health-app/), [Tracxn: Levels profile](https://tracxn.com/d/companies/levels/__KVz0Jg9JCv1iTvep7rdEJaZCJmNgWwAVTCDXbvvgjGo)
- [BetterVitals: Levels review / complaints (affiliate-style, low trust)](https://www.bettervitals.com/learn/levels-health-review)

---

## 2026-10-22 — OneTwenty

OneTwenty Health, Inc. (US) sells a $499/yr longevity membership. It combines quarterly blood
panels, wearable syncing, an AI assistant, a human coach, supplement packs and prescriptions
from partner clinicians. Its stated goal is "one million quality life-years". **It is still
pre-launch.** The site sells "founding member" pricing that "ends at public launch", and no launch
date is given. Press releases show a closed beta opening in Nov 2025, with applications
**capped at 25 people** (255 applied; the published cohort stats cover 21 members, average age 48).
Third-party pages from Oct 2026 call it "open beta". The site names no founders, and we found no
funding round. (Don't confuse it with OneTwenty AG, a Zurich diabetes-algorithm startup that raised
seed money in 2024. Crunchbase and Tracxn mix the two up.) **Main finding:** OneTwenty's design is
retesting. After the baseline, each follow-up panel is chosen from the previous result, and the
protocol is re-tuned every 90 days. It is the first rival we've profiled that changes *which
markers* it tests based on your results.

**Basic features.**
- **Labs:** a 101-marker baseline (hormones, metabolic, inflammation, nutrients). Superpower's
  comparison counts 94–97 per member, including Lp(a), homocysteine, PSA and urinalysis but not
  cortisol, GGT or uric acid. Three targeted retests of 20–40 markers follow, for 161–221 results a
  year. Labs are ordered by an independent licensed provider.
- **Collection:** walk-in draws at a national lab network are included. At-home draws cost $99
  extra, and are the only option in NY/NJ, which is why those members pay $749.
- **Unlimited uploads** of past labs from any provider. The site names Function Health exports as an
  import source, which is a switching hook.
- **Devices:** Oura and Withings (ring, scale, BP cuff) connect directly. Everything else, including
  Dexcom/Libre CGMs, comes through Apple Health or Google Fit. Up to 3 months of history is imported
  at setup, and no device is required.
- **One Health Score (0–100)**, built on the AHA's **Life's Essential 8**.
- A **dedicated human health coach** is included.
- HIPAA-standard security claims (encryption, RBAC, audit logs), "never sells data", deletion on
  request. A LegitScript badge is shown.
- **Not offered:** no e-pharmacy, no insurance billing ("hybrid" option "being explored"), no
  in-house clinicians.

**Advanced features.**
- **Adaptive retesting:** each follow-up panel is targeted from the last result, and the protocol
  (lifestyle → supplements → Rx) is reset every 90 days. The sample review shows deltas such as
  "ApoB density +12%, HRV +22 ms" and a "suggesting root cause" note. These are mock-ups, not member
  data.
- **AI assistant + monthly AI health reviews.** It "answers from your own data" and flags items for
  review. The grounding method is not disclosed and there is no published accuracy.
- **Risk detection → specialist referral** is claimed. The site does not say how risk is computed
  (no trained model is named) or how referral works.
- **Rx via partner telehealth providers** (from $49/mo extra, per Superpower's comparison):
  TRT/HRT, enclomiphene, DHEA, pregnenolone, thyroid, metformin, semaglutide/tirzepatide,
  sildenafil/tadalafil, and a peptide/"wellness" list (sermorelin, GHK-Cu, PT-141, NAD+,
  glutathione, oxytocin nasal).
- **Custom Packs:** supplements formulated from lab results, from $67/mo extra, about 25 SKUs
  (berberine, magnesium, DHEA, NAC, creatine…).
- **Not offered:** no biological-age score, no disease/mortality prediction model, no imaging, no
  genomics or methylation, no CGM supply, no meal-photo nutrition, no safety or caregiver features.

**Pricing (official site, Oct 2026).**
- $499/yr founding price ($749 NY/NJ). The price is expected to rise at public launch (third-party
  pages; the site only says founding pricing ends).
- Add-ons: $99 at-home draw, supplements from ~$67/mo, medications from ~$49/mo (both figures from
  Superpower's competitor-authored page; not shown on OneTwenty's site).
- HSA/FSA "for most members". No insurance.
- A realistic all-in year with packs and one medication is ≈ $1,800–2,000+ (our estimate:
  $499 + 12×$67 + 12×$49).

**Weaknesses.**
- **Unproven, tiny scale.** It has a beta cohort of ~25, no named team, no funding disclosed and no
  outcome data. Even favourable reviewers note it is "still in beta".
- **Low-cost headline, add-on revenue.** The $499 covers labs + app + coach. Supplements, drugs and
  home draws are all extra, and Superpower's page attacks it on exactly this point.
- **"Not a medical practice."** Rx and referrals are outsourced, so there is no continuous clinician
  ownership. The peptide/injectable menu (NAD+, glutathione, GHK-Cu, oxytocin) is thinly evidenced
  and carries regulatory risk (FDA compounding scrutiny).
- **Shallow device layer.** Only two direct integrations, with everything else funnelled through
  Apple Health / Google Fit. There is no raw ECG/PPG and no own hardware.
- **Distribution looks SEO/affiliate-heavy.** Its own "/vs/" pages and blog rank for competitor
  terms, and Crown Counseling "reviews" push OneTwenty with tracking links but no affiliate
  disclosure. Treat any positive third-party coverage as low-trust. We found no Reddit, Trustpilot
  or App Store reviews.
- **Science is thin.** Scoring uses a public AHA framework (sensible but not proprietary). No studies
  are cited, there is no bio-age and there is no predictive model.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Model-driven adaptive retest panels.** OneTwenty targets follow-ups by hand or by rules. We
     can do it from our risk engine: after a baseline, pick the 20–40 markers whose re-measurement
     most changes the user's predicted risk or bio-age (expected information gain per ₹). This is a
     real leapfrog, and it makes quarterly testing affordable in India, where a full panel every
     quarter is not.
  2. **AHA Life's Essential 8 score** as the transparent "basic" composite next to our trained risk
     outputs. All 8 inputs (diet, activity, nicotine, sleep, BMI, lipids, glucose, BP) already exist
     across intake, wearables and bloods. It fills the "no single composite score" ◐ row cheaply and
     is clinically recognised.
  3. **Risk-threshold → referral trigger** in the care graph. When a Telomy risk crosses a band,
     automatically create a referral task for the linked doctor/centre. OneTwenty only claims this;
     our multi-role OS can actually route it.
  4. **Onboarding backfill + switch-in import:** pull months of HealthKit/Health Connect history and
     parse rival lab PDFs (Function/Thorne/Indian labs such as Thyrocare and SRL) on first run.
- *Operational parity via partnership:*
  5. Partner-lab walk-in + home-collection pricing that supports a baseline + 3 small retests. The
     Rx menu stays narrow and evidence-based (metformin, GLP-1, HRT through partner clinicians), and
     we should **not** copy the peptide/injectable catalogue.
- *Our opening:* OneTwenty has the right loop (test → act → retest every 90 days) and an empty
  core: no bio-age, no trained risk or mortality model, no grounded-AI evidence, no hardware, and
  no clinicians of its own. Telomy's models and clinical OS can run the same loop with fewer
  markers per retest and actual predictions. It is also US-only, so the India loop is open.

Sources:
- [OneTwenty homepage (official, © 2026): price, markers, devices, Rx list, FAQ](https://onetwenty.com/)
- [OneTwenty: How it works (official)](https://onetwenty.com/how-it-works), [Mission (official)](https://onetwenty.com/mission)
- [OneTwenty press: closed beta applications open (Nov 2025)](https://onetwenty.com/press/closed-beta-applications-open), [Closed beta cohort breakdown (Nov 2025)](https://onetwenty.com/press/closed-beta-cohort-breakdown)
- [Superpower vs OneTwenty (competitor-authored, updated 20 Oct 2026)](https://superpower.com/biomarker-testing-companies/superpower-vs-onetwenty): marker audit, add-on prices
- [Crown Counseling: Marek vs Geviti vs Function vs Mito (updated 7 Oct 2026; OneTwenty-tracked links, no disclosure, low trust)](https://crowncounseling.com/reviews/marek-vs-geviti-vs-function-vs-mito-health)
- [Startupticker: OneTwenty AG (Zurich diabetes AI) funding, a different company](https://www.startupticker.ch/en/news/onetwenty-secures-first-funding-to-launch-ai-diabetes-technology), [Crunchbase: OneTwenty](https://www.crunchbase.com/organization/onetwenty)

## 2026-10-22 — Apple Health + Apple Watch

Apple's health stack is the Watch (Series 12 / Ultra 4 launched Sep 2026), the iPhone Health app,
AirPods Pro, and a **redesigned Health app with Insights and Longevity tabs and a "Health Age"**.
That app was previewed at the 9 Sep 2026 event, is in the iOS 27.2 beta, and ships "late 2026",
US English first. **Main finding:** Apple is moving from sensor platform into longevity product.
A free, wearable-driven bio-age plus a $119 Quest panel on every US iPhone turns the *basic* tier
of our category into a commodity. It does not touch trained disease or mortality prediction,
clinicians, Rx, or India-specific labs and languages. Apple also delayed its own full AI health
coach.

**Basic features.**
- **Watch vitals.** The Series 12 / Ultra 4 "Health Sensing System" reads HR every 5 s and HRV as
  often as every 5 min, with improved ECG electrode contact. Also: the Vitals app (overnight and
  daytime, labelled wellness-only), respiratory rate, wrist temperature, Blood Oxygen app,
  Activity rings, Workout app, VO2 max with a low-fitness alert, Noise app, Mindfulness app and
  time in daylight.
- **Sleep:** nightly Sleep Score (duration, consistency, wake-ups, stages) and sleep schedule.
- **Readiness (0–10):** labelled Recover / Pace Yourself / Ready / Go For It. It needs Series 12
  or Ultra 4, so older watches don't get it.
- **iPhone Health app:** Medications, Cycle Tracking (new perimenopause/menopause support;
  deviation notifications for users 40+), pregnancy insights, State of Mind logging, clinically
  validated depression/anxiety questionnaires with PDF export, Journal, and vision-prescription
  storage.
- **Health Records:** FHIR pull of labs, conditions, meds and immunizations from 500+ US
  institutions (11,000+ care locations), plus the UK and Canada. We found no India hospital support.
- **Health Sharing / Family Setup** for family members.
- **Safety:** fall detection, crash detection and Emergency SOS. These are long-standing Watch
  features; we did not re-verify India availability for this run.
- **Privacy:** Health data is encrypted on device and end-to-end encrypted in iCloud with 2FA.
- **Not offered:** food logging (nutrition appears only as a Longevity score category), consults,
  e-pharmacy, Rx and CGM hardware. Glucose comes only from third-party apps.

**Advanced features.**
- **Health Age + Longevity tab** (late 2026, US English, needs an Apple Intelligence iPhone and an
  Apple Watch). Inputs are VO2 max, resting HR, HRV, sleep, and optional blood work (A1c, LDL),
  uploaded manually or synced from Health Records. The tab adds domain scores for heart, sleep,
  mental wellbeing, movement, metabolic health, hearing and nutrition, each "classified against
  the latest clinical guidance". There is no published validation. A German fact-check says
  Apple has not shown that it predicts lifespan, and beta users report big swings (one forum post
  went from +5.5 to +10 years).
- **$119 Quest lab panel:** 50+ cardiometabolic and organ-function markers, plus BP, height,
  weight and waist/hip, drawn in-lab at ~2,000 US Quest sites. Results are combined with Watch data
  on the iPhone and explained in clinical-expert videos. It is **not live in the beta** and is US
  only. (Oura sells a similar Quest panel for $99.)
- **Movement assessments:** an at-home VO2 max test plus flexibility, strength, balance and
  movement-mechanics tests using the iPhone camera, processed on device with no video stored. They
  output an exercise plan. The third-party fact-check says the VO2 max validation had ~35
  participants, mostly young and fit.
- **Hypertension notifications:** FDA-cleared Sep 2025, from passive 30-day PPG patterns, for
  people 22+ who are not pregnant and not already diagnosed. Validation: **sensitivity 41.2%,
  specificity 92.3%** (214 of 585 hypertensive people flagged, per AAFP). A Jan 2026 editorial in
  *Hypertension* called it not suitable for large-scale screening. That is relayed by a
  secondary source; we did not read the editorial. **In India it is not available on Series 12 /
  Ultra 4 at launch.** Apple cites pending regulatory clearance and expects it "next year". The
  regulator is not named.
- **Sleep apnea notifications** (Series 9+, Ultra 2+, SE 3, users 18+), plus the ECG app,
  irregular-rhythm notifications and AFib History. Apple's availability page lists India for
  these.
- **AI:** Apple Intelligence Insights, Personal Guidance and For You summaries in the new app.
  **The full paid AI health coach (project "Mulberry", the "Health+" subscription rumour) was
  scaled back** (Bloomberg, Feb 2026), with pieces folded into the Health app. A reduced
  "Quartz" premium tier is rumoured but unconfirmed.
- **AirPods Pro:** hearing test and an FDA-authorized hearing-aid feature. AirPods Pro 3 adds
  workout heart rate.
- **Research app studies** (Heart & Movement, Women's Health, Hearing).

**Pricing.**
- Health app features are free with the device.
- Apple Watch Series 12 starts at **₹56,900 in India** (Apple's India press release, via Mac
  Observer) and C$549 in Canada. We did not check the US price this run.
- The Quest panel is $119 (US, not yet live).
- No Health subscription exists as of this run.

**Weaknesses.**
- **iPhone + Watch lock-in.** Health Age needs a Watch and an Apple Intelligence iPhone, and
  Readiness needs this year's watch. India's mass market is Android (Apple's Indian share is
  well under 10% of smartphones; that figure was not re-verified this run). At ₹56,900, the Watch
  is a premium product.
- **US-first, English-first.** The Longevity tab and the Quest labs are US only. India has no
  hypertension notification on new watches, no Health Records hospitals and no lab partner.
- **Wellness, not medicine.** Vitals, SpO₂ and temperature are "not for medical use". There are no
  clinicians, no consults, no Rx and no care-team workflow beyond PDF sharing. The hypertension
  feature misses ~59% of hypertensive people.
- **No trained disease or mortality prediction.** Health Age is a fitness-and-sleep composite
  with optional A1c/LDL. It does not forecast specific conditions.
- **The AI coach retreat** suggests Apple is wary of giving grounded medical advice from an LLM.
  That leaves room for a tool-grounded assistant.
- **No nutrition engine:** no meal logging and no Indian food database.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Patch-based cuffless BP trend + hypertension screen.** Apple's wrist PPG reaches 41%
     sensitivity, and the feature is blocked on new watches in India. Our patch has ECG + PPG on
     one clock, so pulse-arrival time is available. Calibrate against a cuff in TelomyRec, then
     fuse the result with the disease model's hypertension risk. This is a real leapfrog in our
     home market, but it needs a CDSCO pathway before any diagnostic claim.
  2. **Sleep-apnea screen from overnight SpO₂.** Our ring and oximeter give ODI and nadir SpO₂
     directly, which is stronger than Apple's accelerometer proxy. Route positives to the existing
     HSAT diagnostic in `diagnostics.py`.
  3. **Camera movement assessment → muscular-age clock.** Use on-device pose estimation
     (sit-to-stand, single-leg balance, gait speed) to feed the muscle clock without DXA or grip
     hardware. It matches Apple's Longevity feature and plugs into a model Apple doesn't have.
  4. **Ingest Apple Health rather than compete with it.** Read Health Age inputs, Readiness, Sleep
     Score, cycle data and Health Records labs from HealthKit, and give the same treatment to
     Health Connect on Android, where Apple is absent. Position Telomy as the medical layer
     *above* the OS: trained risk, grounded explanations, clinicians.
- *Operational parity via partnership:*
  5. **A cheap entry panel at India scale.** Apple ($119) and Oura ($99) set the US anchor for a
     ~50-marker cardiometabolic panel. An Indian partner lab (Thyrocare, Redcliffe, Healthians
     tier) with home collection at well under ₹2,000 would undercut both and feed our blood clocks.
- *Our opening:* Apple's longevity layer is US-only, English-only, Watch-gated and deliberately
  non-medical, and its AI coach was pulled back. In India, an Android-first, multilingual,
  clinician-linked product with trained disease/mortality models, Indian foods and a hypertension
  screen Apple can't ship there yet is open ground. Expect Apple to set the *UX bar* (Readiness,
  Sleep Score, Health Age) that Indian users will compare us against.

Sources:
- [Apple Health (official): features, caveats, redesigned Health app late 2026](https://www.apple.com/health/)
- [watchOS 27 feature availability (official, India rows)](https://www.apple.com/watchos/feature-availability/)
- [MacRumors: iOS 27 Health app redesign guide (Health Age, Longevity, $119 Quest panel, US English)](https://www.macrumors.com/guide/ios-27-health-app-new-features/), [MacRumors hands-on, iOS 27.2 beta (16 Sep 2026)](https://www.macrumors.com/2026/09/16/ios-27-2-health-app-beta/)
- [ThePrint: hypertension notification delayed in India on Series 12 / Ultra 4](https://theprint.in/economy/apple-delays-hypertension-notification-on-watch-series-12-in-india-pending-clearances/3038585/), [Mac Observer: Series 12 price ₹56,900 / C$549](https://www.macobserver.com/tips/round-ups/apple-watch-series-12-price-canada-india-uk/)
- [AAFP: Smartwatch screening for hypertension (sensitivity 41.2% / specificity 92.3%)](https://www.aafp.org/pubs/afp/afp-community-blog/entry/smartwatch-screening-for-hypertension.html), [9to5Mac: FDA clearance (Sep 2025)](https://9to5mac.com/2025/09/11/apple-watch-hypertension-alerts-feature-receives-fda-clearance/)
- [Bloomberg: Apple scaling back AI health coach (5 Feb 2026)](https://bloomberg.com/news/articles/2026-02-05/apple-is-scaling-back-plans-for-new-ai-based-health-coach-service), [Macworld: iOS 26.4 beta "Health Coaching" strings](https://www.macworld.com/article/3062678/ios-26-4-beta-suggests-apple-hasnt-given-up-on-its-ai-health-coach.html)
- [Longevity Germany: Apple Health Age fact-check (lower trust, commentary)](https://longevity-germany.com/en/articles/apple-s-longevity-tab-and-health-age-fact-checked), [Gadget Hacks: Readiness / Health Age gating](https://apple.gadgethacks.com/news/apple-health-app-redesign-readiness-score-health-age/), [Android Authority hands-on](https://www.androidauthority.com/apple-google-health-redesign-3712230/)
- [iMore: Health Records expands to UK and Canada](https://www.imore.com/apple-expands-health-records-uk-and-canada)

## 2026-10-22 — WHOOP

WHOOP sells a screenless band (WHOOP 5.0, and WHOOP MG with medical-grade sensors) as a
subscription. Since 2025 it has added a wearable-only bio-age (Healthspan / WHOOP Age), a Quest
blood panel (Advanced Labs), an OpenAI-powered coach, and in 2026 clinician video visits and
medical-record import. **Main finding:** WHOOP is turning a fitness band into a US longevity
clinic: wearable plus labs plus records plus clinicians in one app. Its regulated features (ECG,
BP Insights) and its clinical services are US-only or blocked in India, and its bio-age is a
literature formula, not a trained model. Note: Telomy already ingests WHOOP 4.0 data (NOOP study).

**Basic features.**
- **Band + vitals:** HR, HRV, respiratory rate, SpO₂, skin temperature; 14+ day battery on 5.0.
  Daily **Recovery**, **Strain** (0–21) and **Sleep** scores, sleep coach, stress monitor.
- **Journal:** log behaviours, supplements and life events by voice or text; monthly reports
  on how each behaviour affected recovery. Custom behaviours from free text (18 Sep 2026). A third-
  party developer post says Journal, Coach, and My Memory data are not in WHOOP's public API.
- **Advanced Labs Uploads:** free for all members worldwide; upload outside bloodwork and see it
  next to recovery, sleep and strain.
- **Records:** HealthEx partnership (May 2026) pulls diagnoses, medications and procedures into
  the app, US only, opt-in with disconnect.
- **Not offered:** food logging / meal photo, CGM (CEO has said it is "exploring" glucose, per a
  blog; no announcement found), e-pharmacy, fall detection / SOS, family/caregiver sharing.

**Advanced features.**
- **Healthspan: WHOOP Age + Pace of Aging** (May 2025; Peak and Life only, 18+). Nine wearable
  metrics: sleep hours, sleep consistency, time in HR zones 1–3 and 4–5, strength-training time,
  steps, VO₂ max, resting HR, lean body mass. Each is mapped to published all-cause-mortality
  hazard ratios and converted to an age offset (per third-party analysis of the white paper).
  WHOOP Age uses 6 months; Pace of Aging (−1x to 3x) uses the last 30 days; full calibration
  after 90 days. Built with Eric Verdin (Buck Institute). We found **no peer-reviewed validation**;
  only the company white paper. A CEO interview says it is WHOOP's most popular feature.
- **Advanced Labs** (launched 30 Sep 2025 with Quest): ~65-marker panel, ordered and reviewed
  by a licensed clinician, drawn in-lab at 2,000+ Quest sites, results in 7–10 business days with
  a Coach action plan. Specialized panels (77–90 markers), including a **Women's Health panel**
  (Mar 2026: cycle, perimenopause, thyroid, bone) with hormonal symptom predictions. Launch
  waitlist reportedly 350,000+. US, and UAE via Unilabs (Dhs 733). We found no home-draw option.
- **WHOOP MG:** FDA-cleared single-lead ECG with AFib screening and irregular-rhythm
  notifications; **Blood Pressure Insights** (cuff-calibrated cuffless trend). The FDA sent a
  warning letter over BPI in Jul 2025 and closed it on 24 Jun 2026 after WHOOP changed the
  product and labelling; it may show BP as a wellness signal, not market a BP monitor.
  **In India, ECG is not available** (WHOOP community moderator) and BPI is reported unavailable.
- **AI:** WHOOP Coach on OpenAI (since Sep 2023). May 2026 added **My Memory** (members view,
  edit, delete what the AI knows about them), Proactive Check-Ins, and AI-suggested journal items.
  No published accuracy, grounding method or hallucination testing found.
- **Clinician video visits:** announced 8 May 2026 for US members "this summer", extra fee not
  disclosed; whether clinicians prescribe was "not available at this time". We did not confirm
  that the service is live as of this run.

**Pricing.**
- US: One $199/yr, Peak $239/yr (adds Healthspan, stress, health monitor), Life $359/yr (MG
  hardware, ECG, BPI). New members must start annual. HSA/FSA-eligible.
- Advanced Labs packs on top: $199 (1 test) / $349 (2) / $599 (4) per year, per third-party
  pricing sites (WHOOP's own pages blocked our fetch; treat as unverified). Specialized panels
  ~$299 each (Sacra estimate).
- India: 5.0 with 12-month membership from ₹21,990 at Oct 2026 launch coverage; Peak bundle seen at
  ₹23,990–28,990 on Amazon price trackers. Rupee prices per tier not confirmed.

**Weaknesses.**
- **Regulated features don't reach India.** ECG and BPI on MG are unavailable there; clinician
  visits, records import and Advanced Labs are US (plus UAE labs). An Indian Life buyer pays for
  hardware features they cannot use.
- **Bio-age is a formula, not a trained model.** Literature hazard ratios over nine fitness/sleep
  inputs, with no diet, blood, or disease history, and no published validation. It does not
  predict specific diseases.
- **Billing and trust.** California auto-renewal class action (Jul 2026); privacy suits over
  data sharing via the Segment SDK and biometric-data claims; a BPI "medical-grade" marketing suit.
  These are allegations, not rulings. Reports of MG units going unresponsive soon after setup
  (TechRadar / The Verge, per search summaries).
- **No nutrition, no CGM, no safety agent, no caregiver view.** The coach reasons over behaviour
  and recovery but cannot see what the user eats.
- **Closed data.** Journal, Coach and Memory are not exposed in the public API.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **A trained "Pace of Aging" that updates monthly from wearables and anchors to blood.** WHOOP
     proved users love a fast-moving bio-age number. Ours can be better: train the wearable clock
     against our PhenoAge/blood clocks and the mortality model, so the monthly number is
     calibrated, not a hazard-ratio sum. Publish the validation; WHOOP hasn't.
  2. **Behaviour → impact report.** We already have the habit tracker with personal baselines
     (`trackers.py`) and recovery/strain from the patch. Add a monthly "this habit moved your HRV /
     sleep by X" report with confidence intervals. It's WHOOP's stickiest loop and mostly built.
  3. **User-editable AI memory for Telomy-LLX.** Let users see and delete what LLX knows about
     them. It is a trust feature and a DPDP-Act consent control, and it is cheap.
  4. **AFib + BP from the patch, through CDSCO.** Our AF classifier is validated on AFDB/NSRDB and
     the patch gives ECG + PPG on one clock. WHOOP's ECG is blocked in India; a cleared Indian
     route is a real opening (needs regulatory work before any diagnostic claim).
- *Operational parity via partnership:* a clinician-reviewed lab panel with **home collection**
  (WHOOP is in-lab only) through an Indian lab partner, and Indian doctor teleconsults through the
  doctor workspace we already ship.
- *Our opening:* in India WHOOP is a ₹22k+ band whose medical features are switched off, with no
  food, CGM, labs or clinicians. Telomy should treat WHOOP as a data source (keep the NOOP/API
  ingestion) and sell the medical layer above it.

Sources:
- [Quest newsroom: WHOOP launches clinician-reviewed Advanced Labs (30 Sep 2025)](https://newsroom.questdiagnostics.com/2025-09-30-WHOOP-Launches-Clinician-Reviewed-Advanced-Labs,-Unlocking-a-Comprehensive-View-of-Human-Health), [WHOOP Advanced Labs page](https://shop.whoop.com/us/en/advanced-labs/), [WHOOP support: Advanced Labs](https://support.whoop.com/s/article/Advanced-Labs?language=en_US)
- [WHOOP Membership Pricing (support)](https://support.whoop.com/s/article/Membership-Pricing?language=en_US), [trackervs: WHOOP pricing 2026](https://trackervs.com/pricing/whoop-pricing/), [thepricer: Advanced Labs cost (third-party)](https://www.thepricer.org/how-much-does-whoop-advanced-labs-cost/), [Sacra: WHOOP](https://sacra.com/c/whoop/), [Gulf Business: WHOOP × Unilabs UAE](https://gulfbusiness.com/en/2026/health-care/whoop-unilabs-launch-65-biomarker-testing-in-uae/)
- [WHOOP Healthspan page](https://www.whoop.com/us/en/thelocker/healthspan/), [Healthspan white paper](https://www.whoop.com/us/en/thelocker/Healthspan-Data-Meets-Longevity/), [Podcast 323: the 9 metrics](https://www.whoop.com/us/en/thelocker/podcast-323-the-9-metrics-that-make-up-your-healthspan-with-emily-capodilupo/), [Gadgets & Wearables: science behind Healthspan](https://gadgetsandwearables.com/2025/08/07/science-behind-whoop-health-span/)
- [WHOOP press: 5.0 and MG](https://www.whoop.com/us/en/press-center/whoop-unveils-5.0-MG/), [MassDevice: FDA closes BPI warning letter](https://www.massdevice.com/fda-closes-warning-letter-whoop-blood-pressure/), [Healthcare Dive: same](https://www.healthcaredive.com/news/fda-drops-whoop-warning-letter-over-blood-pressure-feature/823737/)
- [Business Wire: clinician access + new AI features (8 May 2026)](https://secure.businesswire.com/news/home/20260508464188/en/WHOOP-Expands-Health-Platform-with-On-Demand-Clinician-Access-and-New-AI-Features), [CNBC: on-demand clinician access](https://www.cnbc.com/2026/05/08/whoop-on-demand-clinician-access.html), [Fierce Healthcare: HealthEx](https://www.fiercehealthcare.com/health-tech/whoop-healthex-partner-connect-members-ehrs-directly-app-personalized-health-insights), [Terra: Journal / AI coaching / API gaps](https://tryterra.co/blog/whoop-journal-ai-coaching-developer-access), [T3: Advanced Labs Uploads](https://www.t3.com/active/fitness-trackers/whoop-advanced-labs-uploads-rollout)
- [Forbes: WHOOP women's health service (Mar 2026)](https://www.forbes.com/sites/andrewwilliams/2026/03/10/whoop-has-a-new-service-for-womens-health-and-cycle-tracking/), [the5krunner: glucose plans (commentary)](https://the5krunner.com/2025/11/13/whoop-ipo-glucose-monitoring-plans-2026/)
- [TelecomTalk: WHOOP 5.0 India from ₹21,990](https://telecomtalk.info/whoop5-brings-screenless-fitness-tracking-to-india/1012433/), [WHOOP community: ECG not working in India](https://www.community.whoop.com/t/why-ecg-is-not-working-in-india/12376), [pricehistory: Peak bundle Amazon India](https://pricehistory.app/p/whoop-peak-12-month-membership-5-0-Zh0zdtce)
- [ClassAction.org: auto-renewal suit](https://www.classaction.org/news/fitness-tracking-tech-company-whoop-facing-class-action-over-alleged-membership-auto-renewal-practices), [ClassAction.org: data-sharing suit](https://www.classaction.org/news/whoop-facing-class-action-lawsuit-for-allegedly-sharing-users-fitness-tracker-data-without-permission), [AFS Law: FDA letter anchors class action](https://www.afslaw.com/perspectives/longevity-lens/whoop-there-it-fda-warning-letter-now-anchors-class-action-against)

## 2026-10-22 — Oura

Oura sells a smart ring plus a cheap subscription, and since 2025 has built a health platform on
top: AI Advisor, photo meal logging, a Dexcom Stelo CGM tie-in, a $99 Quest blood panel, lab
uploads, US medical-record import, and in 2026 a "Health Radar" layer (Blood Pressure Signals,
Nighttime Breathing), GLP-1 Insights and menopause insights. It is the scale leader: 5.0M paid
members, ~85% 12-month retention, $1.21B revenue in the nine months to Jun 2026 (+74%), profitable,
Nasdaq IPO at roughly $15–16B (S-1 figures as reported; valuation varies by source). **Main finding:**
unlike WHOOP, Oura is shipping its newer wellness features **in India** (Health Radar, BP Signals,
GLP-1 Insights; Ring 5 launched in India today, 22 Oct 2026). Its blood panel, CGM and records stay
US-only, and none of its features predict specific diseases.

**Basic features.**
- **Ring + vitals:** HR, HRV, SpO₂, skin temperature, respiratory rate; Sleep, Readiness and
  Activity scores; Cumulative Stress (Oct 2025 app redesign). Ring 5 (Jun 2026) is ~40% smaller
  than Ring 4, 6–9 day battery. Live Activity Tracking and auto-detection of 40+ activities.
- **Meals** (May 2025): photo a meal, AI tags protein, fibre, processing level, added sugar, fats,
  carbs. Launched for US members; India availability not confirmed.
- **Lab Uploads** (30 Jun 2026): PDFs from any lab, explained by Advisor.
- **Health Records** (Ring 5 launch, US): conditions, medications, allergies, labs.
- **Data Deletion** (Jun 2026, global): erase a chosen time window without closing the account.
- **Not found:** fall detection / SOS, caregiver or family monitoring view, e-pharmacy,
  in-house doctors (Counsel Health is an experiment, below).

**Advanced features.**
- **Cardiovascular Age** (2024): vascular age from PPG pulse-wave velocity. Oura cites an Apr
  2026 NUS study supporting overnight ring-pulse vascular-age estimation (company blog; we did not
  read the paper).
- **Health Panels** (Oct 2025): $99, 50 markers (metabolic, cardiovascular, liver, kidney,
  inflammation), in-lab at 2,000+ Quest sites, HSA/FSA, US 18+, not in AZ/HI/NJ/NY/RI. A comparison
  site reports discounts to ~$74 (unverified). No home draw found.
- **Glucose with Dexcom Stelo** (May 2025): $99 for two 15-day sensors via ouraring.com; Time Above
  Range plus daily AI analysis next to meals/sleep/stress. **US only**, Gen3+, English, adults not on
  insulin (Oura support page, updated 14 Oct 2026).
- **Health Radar** (rolling out Jun–Jul 2026; US, UAE, India; Gen3+): **Blood Pressure Signals**
  watches 30-day nighttime pulse patterns and suggests checking with a cuff; it shows no mmHg and has
  no FDA clearance (launched as a wellness feature under FDA's Jan 2026 wellness guidance). A separate
  FDA-overseen hypertension study reportedly ended Aug 2026; clearance status unknown. **Nighttime
  Breathing** shows a 30-day view of sleep breathing patterns. Grew out of Symptom Radar.
- **GLP-1 Insights** (Jun 2026; US, UAE, India): log doses, schedule, side effects and weight
  alongside sleep, readiness, stress.
- **AI — Oura Advisor** (all members since Mar 2025): chat over the user's ring data. The only
  reliability number is beta users' own rating (83% "reliable"), not an error rate. Feb 2026: Oura's
  first proprietary model, for women's health, drawing on sources reviewed by in-house clinicians.
  No hallucination testing or grounding method published.
- **Women's health:** cycle, pregnancy and perimenopause insights; "Menopause Insights" named at
  the India Ring 5 launch.
- **Counsel Health** (Oura Labs, May 2026): AI-led primary care with licensed physicians; members can
  try it; eligibility and price not stated.
- **Enterprise:** the US DoD is Oura's largest enterprise customer; enterprise runs on Palantir's
  FedStart hosting. CEO says the DoD cannot access consumer data and Oura will never sell data.

**Pricing.**
- US: Ring 5 from $399 (premium finishes to $499); membership $5.99/mo or $69.99/yr. Health Panels
  $99; Stelo $99 per 2 sensors.
- India: membership ₹599/mo, ₹6,999/yr prepaid on Amazon (first month free). Ring 5 ₹39,900 (Silver,
  Black) / ₹50,900 (other finishes), pre-order on Amazon and Croma. Ring 4 is ₹18,900–24,900 in the
  Diwali sale (8 Oct–5 Nov 2026). Ring 5 + one year of membership is over ₹47,000.

**Weaknesses.**
- **Medical layer is US-only.** Blood panel, CGM, records and Counsel Health don't reach India; the
  Indian member gets wearable signals plus a chatbot.
- **Signals, not diagnoses.** BP Signals shows no numbers; Cardiovascular Age and Readiness are
  descriptive. No trained disease or mortality risk, no fusion of blood with wearable data in risk
  models.
- **Accuracy and trust.** Proposed class action *Surber v. Oura* (N.D. Cal., 20 Aug 2026) over the
  "95% sleep staging accuracy" claim (allegations; no class certified). 2025 social-media backlash over
  the DoD/Palantir ties, with some users ditching rings. Advisor has no published accuracy.
- **No safety or caregiver layer.** A ring is well placed for fall/inactivity or night-time distress
  alerts to family, and Oura offers none we could find.
- **Expensive in India** relative to income: ₹40–51k ring plus ₹7k/yr.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **A numeric, calibrated BP path where Oura only gives a "check your cuff" flag.** Our patch gives
     ECG + PPG on one clock (pulse-arrival time), and TelomyRec already does cuff calibration. Ship a
     wellness-labelled nightly BP trend in India first, with published error vs cuff, and start the
     CDSCO route. Oura's India BP Signals launch sets the user expectation; we can beat it on content.
  2. **GLP-1 companion.** Oura has it in India now. We already have a med list, trackers and recovery;
     add dose/side-effect logging plus lean-mass protection (our muscular-age clock and protein from
     meal photos) — Oura can't see muscle loss or protein intake together.
  3. **Illness-onset alert from overnight baselines** (temperature, RHR, HRV, SpO₂ deviation). We hold
     30-night baselines already; this is Oura's Symptom Radar equivalent and a natural feed into the
     safety agent.
  4. **Treat Oura as a data source.** Ingest Oura (API / HealthKit / Health Connect) so its ~₹599/mo
     Indian members can add Telomy's disease risk, blood clocks and clinicians on top.
- *Operational parity via partnership:* home-collected Indian lab panel at a ₹-equivalent of Oura's
  $99 price point (Oura has no India panel and no home draw anywhere); CGM via a sensor that ships in
  India (Oura's Stelo is US-only).
- *Our opening:* Oura's Indian product is signals without diagnosis, labs or doctors. Telomy's trained
  risk models, India labs, doctor workspace and safety agent cover exactly what Oura leaves out — and
  publishing validation with confidence intervals answers the accuracy-trust problem Oura is now being
  sued over.

Sources:
- [Oura blog: new features (28 May 2026)](https://ouraring.com/blog/new-software-features/), [AppleInsider: BP tracking & GLP-1 central to Ring 5](https://appleinsider.com/articles/26/05/28/blood-pressure-tracking-glp-1-tools-central-to-new-oura-ring-5), [MDDI: Ring 5](https://www.mddionline.com/wearable-medical-devices/oura-debuts-world-s-smallest-smart-ring-adding-blood-pressure-insights-glp-1-management-and-more), [Healthline: Ring 5 features](https://www.healthline.com/health-news/oura-ring-5-new-health-fitness-features), [Cardilog: BP Signals limits](https://cardilog.app/blog/oura-ring-blood-pressure), [MedTech Dive: BP feature after FDA policy change](https://www.medtechdive.com/news/oura-to-add-blood-pressure-feature-following-fda-policy-change/821427/), [MedPath: hypertension study](https://trial.medpath.com/news/oura-pursues-fda-clearance-for-blood-pressure-monitoring-feature-in-smart-ring)
- [Oura blog: Health Panels](https://ouraring.com/blog/health-panels/), [Android Central: 50 biomarkers for $99](https://www.androidcentral.com/wearables/oura-ring/oura-ring-users-can-now-access-over-50-blood-biomarkers-for-usd99), [Quest newsroom (1 Oct 2025)](https://newsroom.questdiagnostics.com/2025-10-01-OURA-Debuts-Groundbreaking-Oura-Ring-4-Ceramic-in-Striking-New-Colors), [optimizebiomarkers: Health Panels review (third-party)](https://optimizebiomarkers.com/providers/oura-health-panels)
- [Business Wire: Meals and Glucose (6 May 2025)](https://www.businesswire.com/news/home/20250506997981/en/URA-Redefines-Metabolic-Health-Tracking-with-Two-New-AI-Driven-Features-Meals-and-Glucose), [Oura support: Stelo integration](https://support.ouraring.com/hc/en-us/articles/41171836791443-Stelo-by-Dexcom-Integration)
- [Oura blog: Advisor](https://ouraring.com/blog/oura-advisor/), [Business Wire: Advisor rollout (31 Mar 2025)](https://secure.businesswire.com/news/home/20250331565896/en/Oura-Advisor-an-AI-powered-Personal-Health-Companion-Now-Rolling-Out-to-All-Oura-Members), [Business Wire: proprietary women's-health model (24 Feb 2026)](https://www.businesswire.com/news/home/20260224023927/en/URA-Launches-Its-First-Proprietary-AI-Model-to-Deliver-Personalized-Clinically-Grounded-Womens-Health-Guidance), [Oura blog: NUS vascular-age study](https://ouraring.com/blog/new-nus-research-validates-ouras-vascular-age-estimation/), [MobiHealthNews: heart-health features](https://www.mobihealthnews.com/news/oura-smart-ring-company-extends-heart-health-capabilities), [TechCrunch: redesigned app + Cumulative Stress](https://www.techcrunch.com/2025/10/20/oura-launches-redesigned-app-and-cumulative-stress-feature)
- [Digit: Ring 5 India launch](https://www.digit.in/news/wearable-devices/oura-ring-5-launched-in-india-price-features-and-pre-order-details.html), [The Mobile Indian: Ring 5 India](https://themobileindian.com/news/oura-ring-5-launched-in-india-with-up-to-9-day-battery-life), [Croma: Ring 4 India](https://www.croma.com/unboxed/oura-ring-4-debuts-in-india-price-specs), [gogi.in: Diwali price](https://www.gogi.in/oura-ring-4-diwali-offer-price-india-2026.html), [Amazon India listing](https://www.amazon.in/Oura-Ring-Tracking-Wearable-Fitness/dp/B0D9WVKXLK)
- [SEC: Oura S-1](https://www.sec.gov/Archives/edgar/data/0002133022/000119312526381855/d119865ds1.htm), [TechCrunch: $2.2B IPO](https://techcrunch.com/2026/09/21/ouras-2-2b-ipo-is-mostly-a-payday-for-existing-shareholders/), [CNBC: confidential IPO filing](https://www.cnbc.com/2026/05/21/oura-smart-ring-ipo-filing.html), [valueaddvc: S-1 figures (third-party)](https://valueaddvc.com/pulse/oura-files-ipo-16-billion-valuation-2026)
- [TechCrunch: sleep-tracking accuracy lawsuit](https://techcrunch.com/2026/08/21/oura-faces-lawsuit-accusing-it-of-misleading-consumers-about-sleep-tracking-accuracy/), [MedCity News: lawsuit is about trust](https://medcitynews.com/2026/08/oura-wearable-ring-lawsuit/), [Fortune: CEO on DoD/Palantir](https://fortune.com/2025/09/09/oura-ceo-tom-hale-data-privacy-oura-ring-defense-department-palantir), [Slate: Pentagon partnership](https://slate.com/technology/2025/10/oura-ring-pentagon-department-of-defense-health-wearable.html)

## 2026-10-23 — Ultrahuman (Ring PRO / Blood Vision / M1 / Home / Jade)

*Roster note: the seed entry gave Ultrahuman one line, so it gets a full profile here (next unprofiled
platform after Oura).*

Ultrahuman, from Bengaluru, is the closest thing to a full Telomy-style stack among the wearable
players. It has one app over a ring, its own CGM (M1), a blood-testing service (Blood Vision, home
collection in India through Tata 1mg), an ambient home sensor, and an AI layer (Jade). It sells
hardware **without a mandatory subscription** and makes money from paid add-on modules
("PowerPlugs"). Scale: about 800k rings sold, roughly 12% of users paying for PowerPlugs, a ~$140M
annualised run rate (Aug 2026, management figure), and a $70M round in Sep 2026 at ~$365M from
Qualcomm Ventures, **Labcorp**, Alpha Wave and others. Sacra puts FY26 (to Mar 2026) revenue at about
₹651 Cr / $69M, which is well below earlier ₹1,100 Cr projections. The US is ~45% of revenue and
India ~11%. **Main finding:** Labcorp is now an investor, and the two are researching **ring
blood-flow signals combined with blood tests** for cardiovascular, fertility and aging risk. That is
our bloods × wearables fusion thesis, at research stage, backed by a global lab. And Ultrahuman
already runs Indian home blood collection, which Telomy does not.

**Basic features.**
- **Rings:** Ring AIR (₹28,499 India) and **Ring PRO** (Feb 2026): titanium, up to 15-day battery
  (about 12 in "Turbo" mode), 250 days of storage on the ring, a charging case that holds a year of
  data, and ProRelease (the ring can be cut off a swollen finger). HR, HRV, SpO₂, skin temperature,
  sleep, recovery, VO2 max (algorithm updated Jul 2026), live HR view.
- **Blood Vision:** US Essential plan has 60+ markers, Blood Age and an "AI-powered clinician report"
  for $99, renewing half-yearly. The Annual plan has 120+ markers, two tests a year and "advanced
  Blood Age" for $499. India: from ₹999, base plan ₹1,999 for 60+ markers, premium 100+.
  Phlebotomists from **Tata 1mg** draw at home in 60+ cities / 2,000+ PIN codes (Nov 2025). Also live
  in Saudi Arabia and the UAE, with UK/Australia announced.
- **Vision Cloud** (free, Oct 2025, live in India): upload any lab report for AI summaries and
  trends. CT/MRI support is "planned".
- **Ultrahuman Home:** a screenless room sensor for VOC, CO, CO₂, HCHO, smoke, PM1/2.5/10,
  temperature, humidity, light including UV, and noise. It lists at $549 (it launched at $349 in
  2024) and needs no subscription. Reviews are split; one calls it expensive for what it does.
- **Not found:** in-house or partner doctor consults, prescriptions, e-pharmacy, a caregiver or
  family view, fall detection or SOS, medical-records import.

**Advanced features.**
- **M1 CGM:** 14-day sensor, sold in India. Amazon India snapshots from Jul 2026 show ₹4,099–8,199
  per sensor and ~₹16k for four (price trackers, seller-dependent, unverified). Glucose feeds Jade.
- **Jade AI** (Feb 2026, all users globally): chat in Standard and Deep Research modes over ring,
  Blood Vision, M1 and Home data. It can start breathwork or trigger an AFib check. Ordering food,
  setting room temperature and proactive flags are described as planned. "Jade Pro" is paid, inside a
  "Max" plug-in (6 PowerPlugs + unlimited Jade Pro + UltrahumanX; price not found). No accuracy,
  hallucination testing or grounding method published.
- **Emerald app update** (23 Jul 2026): Engadget reports that **all insight processing now runs on
  device**, so it works without a connection. Other outlets say it runs on the ring; whether Jade's
  language model runs on device is not stated. It also added **UltraSphere**, a "next best action"
  engine with 60+ action types driven by location, weather, profile and biomarkers.
- **PowerPlugs** (paid modules): AFib Detection (nightly PPG bursts using FibriCheck technology;
  company-reported sensitivity 91.9% / specificity 97.6%; first launched where regulators allowed it,
  2024), GLP-1, Cycle & Ovulation Pro (algorithm licensed from viO's FDA-cleared OvuSense; claims 90%+
  vs a multi-hormone method), Respiratory Health (snoring, built with Sleep Cycle), Migraine Insights
  (Click Therapeutics tech), Caffeine Window, Vitamin D, Shift Work, Social Jetlag, Pregnancy, New
  Parent. **Every module is labelled general wellness and none is FDA-authorised itself.** The
  strategy is to license cleared algorithms from others and package them as wellness features. A
  third-party comparison lists ~$3–5/mo per module (unverified).
- **Qualcomm ring** (announced Sep 2026): Qualcomm silicon next to Nordic chips, for more on-device
  compute plus pointer, game-controller, car-key and AI-interface uses, and a third-party developer
  programme.
- **Labcorp research** (Sep 2026): ring blood-flow + blood tests → cardiovascular, fertility and
  aging risk. Exploratory; the CEO gave no details.

**Pricing.**
- Ring PRO $479 (US, case included per most sources; one source says $399 + $100 case). India
  ₹42,990 (TechCrunch; not confirmed on Ultrahuman's India site). Ring AIR ₹28,499.
- No mandatory subscription. PowerPlugs / Jade Pro / Max bundle are optional paid extras.
- Blood Vision US $99 (half-yearly) / $499 (annual); India from ₹999 / ₹1,999. Home $549. M1 see above.

**Weaknesses.**
- **IP and supply.** The Ring AIR is excluded from US import (ITC 337-TA-1398, Oura patent '178,
  final Oct 2025). The redesigned Ring PRO was cleared by CBP on 6 Mar 2026, on condition of
  certification, and CBP can ask for CT scans and manufacturing records. US demand is reported at 18–20×
  supply (TechCrunch). Federal patent litigation continues.
- **Hardware reliability and support** (self-selected reviews): many Ring AIR battery-degradation
  and swelling reports, sleep logged while users were awake reading, SpO₂ that disagreed with a
  medical oximeter, chatbot-only support and multi-week waits. The PRO uses a different battery
  chemistry, so this may not carry over.
- **No clinical layer.** No doctors, no Rx, no referrals. The "clinician report" on Blood Vision
  appears to be AI-written (Athletech). Blood Age has no published method or validation.
- **Signals, not trained risk.** AFib and the other modules are wellness-labelled flags. No disease
  or mortality prediction is shipped. The Labcorp fusion work is research only.
- **No safety or caregiver layer**, even though a 15-day-battery ring worn round the clock is an
  ideal fall or night-time distress sensor.
- **Financial strain:** management says it may not be profitable this year (spending on stores,
  branding and clinical studies), and dollar FY26 revenue growth was ~5% (Sacra estimate).

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Ship the fusion result before Labcorp × Ultrahuman do.** We already have trained bloods ×
     wearables risk models. Publish one validated result (e.g. 10-year CVD risk from blood panel +
     overnight HRV/RHR, with C-index and CIs vs a blood-only baseline). Ultrahuman has the data and
     a lab investor but has published nothing. A preprint makes our claim first and checkable.
  2. **On-device *LLM*, stated plainly.** Ultrahuman now says insight processing is on device, which
     narrows our privacy ★. Ours is stronger: the language model itself (Telomy-LLX/Qwen) runs locally
     and every number comes from a tool call. Say exactly that, and test it (airplane-mode demo, a
     published hallucination test set), since neither Jade nor Oura Advisor publishes either.
  3. **Module packaging.** PowerPlugs show users will pay for single-purpose modules on a free base:
     ~12% attach. We already have the parts (GLP-1 companion, AF classifier, illness alert, circadian
     tools from sleep timing). Offer them as named modules inside the India membership. Where a cleared
     algorithm exists, license it (Ultrahuman's FibriCheck/viO route) rather than rebuild.
  4. **Ingest Ultrahuman data** (API / Health Connect / HealthKit) so India's Ultrahuman owners can add
     Telomy's disease risk, doctors and safety agent on top. They are a ready-made Indian audience.
- *Operational parity via partnership:* **Tata 1mg is the obvious lab-collection partner.** It already
  does home draws for Ultrahuman in 60+ cities, so the integration pattern exists. Match Ultrahuman's
  ₹1,999 / 60-marker price point. For CGM, the M1 itself is sold in India; reading it through Health
  Connect / HealthKit (or Libre) closes our CGM gap without a sensor deal.
- *Our opening:* Ultrahuman has India logistics, its own CGM and an AI chat, but **no doctors, no Rx,
  no trained disease risk, no safety or caregiver features**, and a hardware reliability reputation it
  is still repairing. Telomy's doctor/centre workspaces, risk models and safety agent sit exactly
  there. Our pitch to the Indian family is "your ring sees it, Telomy's doctor acts on it, and your
  family is told."

Sources:
- [Ultrahuman press release: Ring PRO + Jade (27 Feb 2026)](https://cyborg.ultrahuman.com/press-releases/ultrahuman-unveils-ring-pro-with-category-defining-15-day-battery-and-jade-worlds-first-real-time-biointelligence-ai), [TechCrunch: Ring PRO awaits US clearance (India price)](https://techcrunch.com/2026/02/27/ultrahuman-unveils-new-smart-ring-as-it-awaits-u-s-clearance-after-oura-dispute), [Wellworthy: Ring PRO + Jade](https://wellworthy.com/ultrahuman-just-launched-its-most-advanced-ring-yet-alongside-an-ai-that-acts-on-your-health-data-in-real-time/), [Gadgets & Wearables: Jade AI](https://gadgetsandwearables.com/2026/03/17/ultrahuman-jade-ai/), [Android Central: Ring PRO + Jade](https://www.androidcentral.com/wearables/ultrahuman/ultrahumans-ring-pro-cruises-with-15-day-battery-brings-biointelligent-jade-ai-to-users)
- [Engadget: app brings all analysis on device (23 Jul 2026)](https://www.engadget.com/2220780/ultrahuman-overhauls-app-brings-all-of-its-analysis-on-device/), [Digital Health News: Emerald + UltraSphere](https://www.digitalhealthnews.com/ultrahuman-launches-emerald-update-with-redesigned-app-ultrasphere-decision-engine-improved-vo-max-accuracy), [Trusted Reviews: app upgrade](https://www.trustedreviews.com/news/the-ultrahuman-smart-ring-app-just-got-a-huge-upgrade), [Yahoo Tech: UltraSphere](https://tech.yahoo.com/wearables/articles/ultrahumans-major-emerald-adds-ultrasphere-182251700.html)
- [Ultrahuman blog: Blood Vision US](https://www.ultrahuman.com/blog/introducing-blood-vision-with-ultratrace/), [Ultrahuman blog: Blood Vision Essential](https://www.ultrahuman.com/blog/introducing-blood-vision-essential/), [Ultrahuman US shop](https://www.ultrahuman.com/us/shop/), [Athletech: Vision Cloud + Essentials (2 Oct 2025)](https://athletechnews.com/ultrahuman-ai-powered-medical-advice-blood-testing-service/), [The Gadgeteer: Blood Vision review](https://the-gadgeteer.com/2025/07/15/ultrahuman-blood-vision-review-knowledge-is-power-for-your-health/)
- [BW Businessworld: Blood Vision + Vision Cloud India](https://www.businessworld.in/article/ultrahuman-blood-vision-vision-cloud-india-launch-preventive-health-578952), [Outlook Business: Tata 1mg partnership, 60+ cities](https://www.outlookbusiness.com/deeptech/tech/ultrahuman-partners-with-tata-1mg-to-further-expand-its-blood-vision-service-to-over-60-cities-across-the-country), [T2 Online: India rollout](https://t2online.in/tech/tech-news/ultrahuman-expands-blood-vision-diagnostics-to-60-plus-indian-cities-with-tata-1mg-partnership/2001971), [GSMArena: India Blood Vision](https://fo.gsmarena.com/ultrahuman_expands_blood_vision_across_india_introduces_vision_cloud_for_personalized_health_insight-news-70195.php), [price-history.in: M1 Amazon India snapshot (third-party)](https://price-history.in/product/ultrahuman-m1-cgm-glucose-monitor-device-0depSHIm)
- [TechCrunch: Ring AIR AFib detection (2024)](https://techcrunch.com/2024/07/16/ultrahumans-smart-ring-gets-fda-approved-afib-detection), [Medical Device Network: AFib PowerPlug](https://www.medicaldevice-network.com/news/ultrahuman-adds-afib-detection-feature-to-ring-air-smart-ring/), [Circular: Ring PRO add-on prices (competitor, third-party)](https://www.circular.xyz/post/ultrahuman-ring-pro-vs-circular-ring-2)
- [The Gadgeteer: Ultrahuman Home review](https://the-gadgeteer.com/2025/07/18/ultrahuman-home-review-a-fitness-tracker-for-your-living-space/), [T3: Home announced](https://t3.com/news/smart-ring-brand-ultrahuman-introduces-new-tracking-device-that-monitors-your-home)
- [TechCrunch: Qualcomm backs Ultrahuman, $70M (3 Sep 2026)](https://techcrunch.com/2026/09/03/qualcomm-backs-ultrahuman-in-70m-round-on-bet-to-turn-smart-rings-into-computers/), [Ultrahuman press release: $70M round](https://cyborg.ultrahuman.com/press-releases/ultrahuman-raises-70-million-to-build-the-next-generation-of-human-computer-interface-for-health), [HIT Consultant: $70M + Labcorp](https://hitconsultant.net/2026/09/03/ultrahuman-raises-70m-qualcomm-ventures-labcorp-human-computer-interface-health/), [Sacra: revenue estimates (third-party)](https://sacra.com/c/ultrahuman/), [Entrackr: FY26 projection](https://entrackr.com/interview/ultrahuman-projects-rs-1100-cr-revenue-in-fy26-eyes-deeper-international-expansion-10543504)
- [Oura: ITC ruling](https://ouraring.com/blog/oura-itc-case/), [Business Wire: ITC rules for Oura](https://www.businesswire.com/news/home/20250909387922/en/U.S.-International-Trade-Commission-Rules-in-Favor-of-URA-in-Patent-Case-Against-Ultrahuman-and-RingConn), [Android Authority: US ban](https://www.androidauthority.com/ultrahuman-us-ban-3609467/), [The Gadgeteer: banned ring is back (25 Mar 2026)](https://the-gadgeteer.com/2026/03/25/ultrahumans-banned-smart-ring-is-back-with-a-point-to-prove/), [Tom's Guide: Ring PRO coming to US](https://www.tomsguide.com/wellness/smart-rings/bad-news-for-oura-the-subscription-free-ultrahuman-ring-pro-is-officially-coming-to-the-u-s)
- [Trustpilot: Ultrahuman reviews](https://www.trustpilot.com/review/www.ultrahuman.com), [WearableBeat: Ring AIR battery review (2026)](https://wearablebeat.com/articles/ultrahuman-ring-air-review-2026/), [SlashGear: user reviews](https://www.slashgear.com/1875862/ultrahuman-ring-worth-it-user-reviews)

## 2026-10-23 — Garmin (Connect / Connect+ / Venu 4 / fēnix 9 / Index sensors / Garmin Health)

*Roster note: next unprofiled platform after Ultrahuman. Research run 2026-10-23. Garmin's Q3 2026
results were not yet published at research time.*

Garmin is the largest sports-wearable company that also sells health. Its fitness segment grew 42% in
Q1 2026 ($547M) and 25% in Q2 2026 (64% gross margin, 37% operating margin; SEC 8-K). A third-party
estimate puts Garmin Connect at about 45M active users (the5krunner, not a company figure). Its health
offer is a free app with many metrics, a paid **Connect+** tier (Mar 2025), and Garmin Health, an
enterprise SDK/API used in remote monitoring and clinical trials. **Main finding:** Garmin has the best
hardware safety stack of any rival we have profiled: incident detection, fall detection on Venu 4, and
satellite/LTE SOS to a staffed 24/7 Garmin Response centre. Its paid AI layer is widely mocked as
generic, though. Safety plus AI that adds nothing new is the gap a grounded, risk-computing assistant
can fill.

**Basic features.**
- **Vitals:** 24/7 HR, HRV, SpO₂ (Pulse Ox), respiration, skin temperature, sleep stages and sleep
  score, stress, Body Battery and Training Readiness (Firstbeat-derived), VO2 max.
- **Index sensors:** Index Sleep Monitor ($169.99, Jun 2025), a screenless armband with about a week of
  battery, a vibrating alarm and skin-temperature cycle predictions. It works without a subscription.
  Index BPM is a separate cuff blood-pressure monitor that syncs to Connect (price and FDA status not
  found). There is also an Index smart scale.
- **Nutrition** (Connect+ only, Jan 2026): food database, barcode scan, saved meals, logging from the
  watch, and AI photo logging. One hands-on reviewer said the photo guesses are generally good, and a
  Garmin spokesperson said accuracy is being improved.
- **Lifestyle logging:** caffeine, alcohol and other habits, with reports on how they affect sleep,
  stress and HRV. It moved onto the watch in the Feb 2026 update.
- **Coaching:** Garmin Run, Cycling and Fitness Coach plans. The Fitness Coach in the Feb 2026 update
  covers cardio, strength and 25+ activity types.
- **Accessibility** (Feb 2026): spoken time and health data, plus colour-blind display modes.
- **Not found:** doctor consults, prescriptions, e-pharmacy, lab or blood testing, medical-records
  import, CGM integration.

**Advanced features.**
- **ECG app:** FDA-cleared (K221774, Jan 2023), over the counter, AFib vs sinus rhythm, 30-second
  recording. Adults 22+ only, not available in all regions. Runs on Venu 2 Plus/3/4, fēnix 7 Pro and
  later, and MARQ Gen 3. **I found no confirmation that it is enabled in India.**
- **Health Status** (Venu 4 + Index Sleep Monitor, still beta): compares overnight HR, HRV,
  respiration, skin temperature and SpO₂ with a personal 3–4-week baseline and flags drift. It is
  Garmin's version of an illness/strain alert and makes no diagnostic claim.
- **Sleep Alignment + Optimal Sleep Window** (Feb 2026): sleep timing against an inferred circadian
  rhythm, plus a suggested bed and wake window built from about 3 weeks of data.
- **Fitness Age:** derived from VO2 max; newer watches also use resting HR, activity intensity and
  BMI/body fat. No published validation found. The cap on how far below real age it can go (~10 years)
  dates from 2021 (the5krunner, unverified).
- **Safety:**
  - **Incident detection** during GPS activities on most running and outdoor watches. It needs the
    paired phone with data, shows a cancel countdown, then messages the user's contacts.
  - **Fall detection only on Venu 4.** It is off in wheelchair mode.
  - **Manual assistance request** sends name, LiveTrack link and GPS location.
  - **inReach satellite + LTE SOS** to the staffed 24/7 Garmin Response centre on fēnix 8 Pro, fēnix 9
    Pro (Aug 2026, from $1,099.99; inReach now on all Pro sizes) and MARQ Gen 3. A paid connectivity
    plan is required.
  - Garmin's manuals say these features "should not be relied on" as a primary way to get emergency
    help. Except through Garmin Response, the Connect app does not contact emergency services itself.
- **Family sharing:** LiveTrack (Connect+ texts loved ones when an activity starts) and Garmin Locate
  (location through Garmin Messenger over LTE). These cover activity and location only. There is no
  caregiver health view.
- **Active Intelligence** (Connect+): AI text insights over training, sleep and nutrition, for example
  how late eating affects sleep. No grounding method or accuracy data published.
- **Garmin Health (enterprise):** SDK/API with raw-data access. Deployments include Aparito oncology
  remote monitoring, Qurasoft COPD monitoring in Germany (500+ patients on Venu Sq), the REMOTE
  HF-ACTION heart-failure trial and an ActiGraph research collaboration. It is positioned for
  corporate wellness, population health and patient monitoring.
- **R&D signal:** a Feb 2026 Garmin patent describes estimating HbA1c by pulse spectroscopy (reported
  by a rumour/blog site; nothing shipped).

**Pricing.**
- Connect free. **Connect+ $6.99/mo or $69.99/yr**, 30-day trial (2026 secondary sources; no
  Garmin pricing page found in search). Garmin says existing free features stay free, but it has said
  more new features will likely be paywalled (TechRadar).
- Venu 4 $549.99 US (one source: 41 mm $599.99). In India listings conflict: Flipkart and Smartprix
  show ₹73,990, while a review gives ₹48–49k at launch (unverified).
- fēnix 9 from $999.99, fēnix 9 Pro from $1,099.99, MARQ Gen 3 ~$2,500–3,100 (aggregator figure).
  Index Sleep Monitor $169.99. inReach/LTE need a separate plan.

**Weaknesses.**
- **Paid AI is weak.** TechRadar tested 11 Active Intelligence insights and found generic platitudes,
  basic maths and some wrong information. Reviews from 2025 and Apr 2026 (the5krunner) still say
  Connect+ is not worth paying for. Users openly mock it on the Garmin subreddit, and the paywall
  caused a backlash.
- **Fitness, not medicine.** No labs, doctors, Rx or disease risk. Fitness Age is VO2-max arithmetic
  rather than a validated biological-age clock.
- **Safety is fragmented by model and price.** Fall detection is on one watch. SOS to a staffed
  centre needs a ₹1 lakh-class watch plus a plan. Everything else depends on a paired phone with data.
  Alerts go to contacts and nobody clinical sees them.
- **India is a premium import market.** Prices are high, ECG availability in India is unconfirmed,
  and there is no Indian-language health layer or local clinical partner.
- **Software quality:** recent fixes for an optical-HR-sensor bug (fēnix 8, Oct 2026) and resets on
  budget Forerunners suggest firmware QA pressure as features pile up (spyingbee aggregator).

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Paid AI that computes, not paraphrases.** Garmin's lesson is that users reject AI that restates
     their dashboard. Every Telomy-LLX paid insight should produce something new and checkable: a risk
     change with its C-index-backed model, a likely cause from the personal baseline engine, or one
     next action. Show the numbers behind each one, which the grounded tool calls already give us.
  2. **Fall detection on any device, not one model.** Garmin limits fall detection to Venu 4. Our safety
     agent already does fall + confirm + consent escalation. Make it run from **any** phone (and from
     Garmin data through the Health API where possible) and add a clinical step: a Telomy doctor or
     centre gets the event, not only family.
  3. **Health Status-style drift alert, using what we already have.** We have personal 30-night baselines
     (recovery) but no illness-onset alert (matrix row "Proactive illness / strain alert"). Garmin,
     Oura and WHOOP all ship one. Build it from the baselines and route it to the doctor workspace.
  4. **Ingest Garmin through the Garmin Health API** so India's (affluent, older) Garmin owners get
     bloods, disease risk and clinicians on top. Garmin's own enterprise customers (RPM, trials) show
     the API supports clinical use.
- *Operational parity via partnership:* for **SOS with a human in the loop**, Garmin pays for a staffed
  response centre. In India, partner with an ambulance aggregator or 112-integrated dispatcher rather
  than build one. Keep ECG/AFib wellness-labelled until a regulatory path exists. Garmin's ECG
  clearance shows the bar (OTC 510(k), age 22+).
- *Our opening:* Garmin has the best rugged hardware and safety features, but **no labs, no doctors, no
  disease risk, a mocked AI tier, and premium-only Indian pricing**. Our pitch to Garmin owners is
  "keep your watch; Telomy adds the blood test, the risk model and the doctor."

Sources:
- [Garmin newsroom: fēnix 9 / fēnix 9 Pro (25 Aug 2026)](https://www.garmin.com/en-US/newsroom/press-release/outdoor/garmin-expands-its-flagship-performance-smartwatch-lineup-with-fenix9-and-fenix9-pro/), [Garmin newsroom: feature updates (24 Feb 2026)](https://www.garmin.com/en-US/newsroom/press-release/wearables-health/garmin-announces-feature-updates-for-select-smartwatches/), [Garmin newsroom: MARQ Gen 3](https://www.garmin.com/en-US/newsroom/press-release/wearables-health/meet-the-third-generation-marq-collection-from-garmin-premium-tool-watches-designed-for-lifes-most-ambitious-pursuits/), [Garmin newsroom: Venu 4](https://www.garmin.com/en-US/newsroom/press-release/sports-fitness/take-steps-towards-a-healthier-lifestyle-with-the-venu-4-from-garmin/)
- [Garmin blog: running safety (fall detection Venu 4 only; Garmin Response)](https://www.garmin.com/en-US/blog/fitness/how-garmin-helps-you-run-safely/), [Venu 4 manual: safety and tracking](https://www8.garmin.com/manuals/webhelp/GUID-2CF5620C-E585-4E0A-9CC3-9565533EEE4D/EN-US/GUID-64F677A5-03E0-453F-BFE3-E1B93D6FA3FC.html), [Forerunner 165 manual: safety](https://www8.garmin.com/manuals/webhelp/GUID-607F08F6-33FC-40BF-9727-84E54043D82D/EN-US/GUID-64F677A5-03E0-453F-BFE3-E1B93D6FA3FC.html)
- [Gadgets & Wearables: Health Status](https://gadgetsandwearables.com/2025/10/06/garmin-health-status/), [the5krunner: Health Status](https://the5krunner.com/2025/09/20/garmin-health-status-everything-you-need-to-know/), [the5krunner: Q1 2026 update](https://the5krunner.com/2026/02/24/garmin-q1-2026-feature-update/), [DC Rainmaker: Venu 4 hands-on](https://www.dcrainmaker.com/2025/09/garmin-venu-4-hands-on-everything.html), [PhoneArena: Venu 4 pricing](https://www.phonearena.com/news/garmin-venu-4-is-here-12-day-battery-fitness-tools-ready-to-take-on-apple-watch-11_id174133)
- [Engadget: Connect+ food tracking (CES 2026)](https://www.engadget.com/wearables/garmin-food-tracking-feature-connect-plus-ces-2026-043231948.html), [Forbes: Garmin food tracking (5 Jan 2026)](https://www.forbes.com/sites/andrewwilliams/2026/01/05/garmin-watches-can-now-track-food-macros-and-nutrition/), [Android Central: nutrition AI](https://www.androidcentral.com/wearables/garmin-nutrition-tracking-relies-on-ai-to-log-food-and-recommend-dietary-changes), [Garmin blog: nutrition goals](https://www.garmin.com/en-CA/blog/news/stay-on-top-of-nutrition-goals-in-garmin-connect/)
- [Forbes: Connect+ launch](https://www.forbes.com/sites/andrewwilliams/2025/03/27/garmin-owners-now-have-to-pay-to-unlock-features-thanks-to-connect/), [DC Rainmaker: Connect+ walkthrough](https://www.dcrainmaker.com/2025/03/garmin-connect-plus-subscription-walkthrough.html), [TechRadar: 11 Active Intelligence insights](https://www.techradar.com/health-fitness/smartwatches/garmins-new-subscription-ai-feature-is-hilariously-bad-so-far), [TechRadar: more features likely paywalled](https://www.techradar.com/health-fitness/smartwatches/garmin-quietly-confirms-our-worst-fears-about-garmin-connect-says-more-features-will-likely-be-paywalled-in-the-future), [the5krunner: Connect+ review (20 Apr 2026)](https://the5krunner.com/2026/04/20/garmin-connect-plus-review/), [ShouldITrain: Connect+ 2026 pricing (third-party)](https://www.shoulditrain.com/blog/garmin-connect-plus-review)
- [TechCrunch: FDA-cleared ECG app (Jan 2023)](https://techcrunch.com/2023/01/24/garmin-new-fda-cleared-ecg-app-venu-2-plus/), [FDA 510(k) K221774 summary (Innolitics)](https://510k.innolitics.com/device/K221774), [Tom's Guide: Index Sleep Monitor launch](https://www.tomsguide.com/wellness/sleep-tech/garmin-launches-new-index-sleep-monitor-for-screenless-sleep-tracking), [road.cc: Index Sleep Monitor review](https://road.cc/content/review/garmin-index-sleep-monitor-317941), [TechRadar: Index BPM](https://www.techradar.com/news/garmins-new-gadget-capitalizes-on-missing-smartwatch-feature), [TechRadar: features wanted in 2026 (no on-watch hypertension)](https://www.techradar.com/health-fitness/smartwatches/3-new-features-i-want-to-see-from-garmin-in-2026)
- [Garmin blog: Aparito oncology RPM](https://www.garmin.com/en-US/blog/health/remote-patient-monitoring-and-oncology-clinical-trial-opportunities-with-aparito-and-garmin/), [Garmin blog: Qurasoft COPD telemedicine](https://www.garmin.com/en-US/blog/health/telemedicine-solutions-for-remote-patient-monitoring-and-care-management-with-garmin-and-qurasoft/), [Applied Clinical Trials: Garmin × ActiGraph](https://www.appliedclinicaltrialsonline.com/view/garmin-health-collaborates-actigraph-wearable-solutions-clinical-trials), [ClinicalTrials.gov: REMOTE HF-ACTION protocol](https://cdn.clinicaltrials.gov/large-docs/66/NCT04629066/Prot_000.pdf)
- [Garmin blog: Fitness Age](https://www.garmin.com/en-GB/blog/?p=11062), [the5krunner: Fitness Age model](https://the5krunner.com/2019/11/05/garmin-the-biological-age-model/), [HMMüller: fēnix 9 / HbA1c patent (rumour)](https://hmmuller.com/garmin-fenix-9-2026-what-we-know/), [spyingbee: Garmin Oct 2026 updates (aggregator)](https://spyingbee.com/updates/garmin/2026-10)
- [PR Newswire: Garmin Q1 2026 results](https://www.prnewswire.com/news-releases/garmin-announces-first-quarter-2026-results-302756584.html), [SEC 8-K Q2 2026](https://www.sec.gov/Archives/edgar/data/0001121788/000119312526322113/grmn-ex99_1.htm), [SGI Europe: Q1 2026 fitness +42%](https://www.sgieurope.com/financial-results/garmin-fitness-segment-up-42-in-record-q1/120860.article), [the5krunner: ~45M Connect users (estimate)](https://the5krunner.com/2026/05/01/garmin-connect-users-2026/)
- [Smartprix: Venu 4 India price](https://www.smartprix.com/smartwatches/garmin-venu-4-smartwatch-ppd1mg3fnm8y), [Flipkart: Venu 4](https://www.flipkart.com/garmin-venu-4-smartwatch/p/itm7f8e599e8d3fd), [Fat Marathoner: Venu 4 review (India launch price)](https://fatmarathoner.com/garmin-venu-4-review/)

## 2026-10-23 — Fitbit / Google Health (Google Health app · Health Coach · Health Guardian · Pixel Watch 4/5 · Fitbit Air)

*Roster note: next unprofiled platform after Garmin. Research run 2026-10-23 from Google's blog and
store pages, plus TechCrunch, Engadget, Android Authority, Android Police and other reviews. Several
figures come only from third-party sources; these are flagged.*

Google renamed the Fitbit app **Google Health** on 19 May 2026, and Fitbit Premium became **Google
Health Premium**. The app now carries Google wearables, third-party data from Health Connect and Apple
Health, US medical records, and the Gemini-based **Google Health Coach**. Hardware is Pixel Watch 4/5
plus the screenless **Fitbit Air** band. **Main finding:** Google is the first rival to ship a
*wearable-only insulin-resistance estimate* (Health Guardian, autumn 2026), and it is backed by a
*Nature* paper. That puts Google on our disease-risk ground. Its coach still has hallucination
complaints, and its medical-records and SOS features are US-only. In India it is sold as premium
hardware.

**Basic features.**
- **Vitals:** HR, HRV, SpO₂, skin temperature, sleep staging (accuracy update in app v4.68, Apr 2026),
  sleep score, readiness, irregular-rhythm (AFib) alerts, ECG on Pixel Watch.
- **Fitbit Air:** screenless band, $99 US / **₹13,999 India** (Google Store, Flipkart, Croma, Reliance
  Digital; on sale since 2 Oct 2026). About a week of battery, 5 ATM, no GPS. Includes a 3-month Premium
  trial; basic tracking stays free.
- **Pixel Watch 5:** India from ₹42,900 (41 mm, Google Store), on sale 20 Aug 2026. Pixel Watch 4 India
  ₹39,900. **Indian models are Wi-Fi only.**
- **Nutrition:** conversational and photo food logging inside the coach. One tester found some entries
  tens to hundreds of kcal off, and Google has published no accuracy figure.
- **Records (US only):** pulled through **b.well** (FHIR aggregator, Oct 2025 partnership) after a
  **CLEAR** ID + selfie check. Covers labs, meds, vaccines, vitals, procedures, conditions and visits,
  with sharing through SMART Health QR codes. Google says records are not used for ads.
- **Interop:** Health Connect on Android, including FHIR medical-records APIs (per a developer blog).
  Google Fit users will be invited to migrate into Google Health.
- **Not found:** doctor consults, Rx, e-pharmacy, a consumer lab panel to buy, CGM product, human
  coaches.

**Advanced features.**
- **Google Health Coach (Gemini):** public preview Oct 2025, generally available with the app in May
  2026, Premium only (one guide says 37 countries, unverified). Builds workout plans, sends check-ins
  and sleep advice, and summarises and answers questions on medical records. Google has published no
  accuracy figures or grounding method.
- **Health Guardian** (Pixel Watch 5 launch, Aug 2026; features live since about Sep–Oct 2026):
  - Irregular rhythm, high/low HR alerts, Loss of Pulse Detection and ECG.
  - **Monthly blood-pressure trends:** uncalibrated, estimated from pulse wave and motion, no cuff. Not
    FDA-cleared, CE-marked for some EU markets, called "Vascular Stress" in Japan and Mexico.
  - **Sleep breathing quality**, reported monthly.
  - **Insulin Resistance Trends:** a monthly estimate from wrist sensors plus profile data. Google says
    it is not a diabetes prescreener, not for medication changes, and not for pregnant users. It is
    free on Pixel Watch 3/4/5 and needs Premium on Fitbit Air (per Sahha, a third party).
  - India availability of the BP and insulin-resistance features is **not confirmed**.
- **Science base:** the WEAR-ME study (Fitbit × Quest; participants ordered blood tests in-app)
  produced *"Insulin resistance prediction from wearables and routine blood biomarkers"*, published in
  *Nature* in 2026. Few consumer rivals have peer-reviewed validation for a risk feature.
- **Safety:**
  - **Fall detection** (help page lists India).
  - **Loss of Pulse Detection:** prompts an emergency call. Available in 16 countries; India not
    confirmed. Google says it may miss events and is not meant for people with existing heart
    conditions.
  - **Satellite SOS:** US only, LTE models.
  - In India the Wi-Fi watch has to place emergency calls through the paired phone.
- **Family/caregiver:** no caregiver health view found.

**Pricing.**
- Google Health Premium **$9.99/mo or $99.99/yr**, up from Fitbit Premium's $79.99/yr (Android
  Authority). It is included with **Google AI Pro/Ultra**.
- India: **₹499/mo or ₹4,999/yr** after the trial, from one Indian report. Not confirmed on a Google
  page.
- Jio gave eligible users 18 months of Google AI Pro free (Oct 2025). I found no source saying Health
  Premium is part of that India bundle. If it is, the coach reaches millions of Indians at no cost, so
  this is worth watching.

**Weaknesses.**
- **The coach makes errors.** Reviewers saw it misread metrics and build activity plans on wrong data,
  show wrong numbers in notifications until the app was refreshed (with similar reports on Reddit),
  keep raising an old injury after being told to stop, and remember a lot with **no memory dashboard
  and no way to make it forget**.
- **Rebuild regressions.** Features users relied on daily went missing in the May rebuild. Updates
  through July restored some of them.
- **US-centric.** Records, satellite SOS, probably the BP and IR trends, and Loss of Pulse may not
  reach India. The Indian watch has no LTE.
- **Indian pricing.** The Air costs ₹13,999 against $99 in the US. TechCrunch says the price "might
  deter the masses".
- **No clinical loop.** There are no doctors, Rx or lab ordering, and BP and IR are monthly wellness
  trends with no clinician pathway.
- **Trust.** Google plus health data invites scepticism; outlets ran pieces asking whether users should
  trust it. The support pages also mention employer and insurer partnerships.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **An insulin-resistance score, made for India and anchored to bloods.** Google estimates insulin
     resistance from the wrist using a US cohort. We should compute **HOMA-IR / TyG index** from a cheap
     fasting panel, add it to the chronic-risk model, and then train a wearable-only estimate calibrated
     to Indian users. South Asians develop insulin resistance at lower BMI, which a US-trained model
     will likely miss. Ship it as a measured risk with a doctor pathway, not a monthly "trend".
  2. **Monthly health summary with a clinician hand-off.** Health Guardian is a monthly digest (BP,
     breathing, IR). Telomy-LLX can generate the same digest from our ring, patch and oximeter data,
     every number grounded in a tool call, and route out-of-range results to the doctor workspace.
  3. **Editable AI memory.** Google's coach has none and reviewers complain about it. A "what Telomy
     knows about you / forget this" screen is cheap, builds trust, and serves DPDP erasure rights (matrix
     row "User-viewable / editable AI memory").
  4. **Loss-of-pulse trigger in the safety agent.** We already handle fall → confirm → escalate. A
     no-pulse event from the ring/patch could feed the same flow, after false-alarm testing.
- *Operational parity via partnership:* for records, use **ABHA/ABDM** consent-manager pulls instead of
  a b.well + CLEAR style stack; the Indian government already runs the rails. For emergency calls on a
  Wi-Fi-only setup, partner with an ambulance or 112-integrated dispatcher.
- *Our opening:* Google has the strongest science signal of the wearable giants (*Nature* IR paper) but
  **no doctors, no labs, US-only records and SOS, and a coach with reported errors**. In India it sells
  ₹14k–46k hardware. Our pitch: "bring your Fitbit or Pixel data through Health Connect; Telomy adds the
  blood test, India-calibrated risk and a doctor." **Watch item:** if Google puts Health Premium into
  the Jio AI Pro bundle, chat-style coaching becomes free in India. Telomy then has to charge for
  clinical outputs, not chat.

Sources:
- [Google blog: Fitbit personal health coach updates 2026 (medical records, sleep, metabolic)](https://blog.google/products-and-platforms/devices/fitbit/fitbit-personal-health-coach-updates-2026/), [Google blog: coach public preview](https://blog.google/products-and-platforms/devices/fitbit/personal-health-coach-public-preview/), [Google blog: Health Guardian](https://blog.google/products-and-platforms/products/google-health/pixel-watch-health-guardian/), [Google blog: Health Guardian features live](https://blog.google/products-and-platforms/products/google-health/health-guardian-features-live/), [Google blog: Pixel Watch 5](https://blog.google/products-and-platforms/devices/pixel/pixel-watch-5/), [Google blog: Fitbit × Quest metabolic study](https://blog.google/products/fitbit/new-quest-fitbit-study-metabolic-health/)
- [Google Store: Google Health Premium](https://store.google.com/product/google_health_premium?hl=en-US), [Google Store: Introducing the Google Health app](https://store.google.com/magazine/google-health-app), [Google Store India: Pixel Watch 5](https://store.google.com/in/product/pixel_watch_5?hl=en-IN), [Pixel Watch Help: safety features](https://support.google.com/googlepixelwatch/answer/12663810?hl=en), [Medicare.gov: Google Health app listing](https://www.medicare.gov/health-apps/google-health)
- [Nature: Insulin resistance prediction from wearables and routine blood biomarkers](https://www.nature.com/articles/s41586-026-10179-2), [arXiv preprint](https://arxiv.org/html/2505.03784v1), [MobiHealthNews: Fitbit × Quest](https://www.mobihealthnews.com/news/fitbit-quest-partner-study-metabolic-health-using-wearable-data)
- [TechCrunch: revamped app + Gemini coach (Oct 2025)](https://techcrunch.com/2025/10/27/fitbits-revamped-app-with-gemini-powered-health-coach-rolls-out-to-premium-users/), [TechCrunch: Fitbit Air India launch (30 Sep 2026)](https://techcrunch.com/2026/09/30/google-launches-fitbit-air-in-india-though-its-high-price-might-deter-the-masses/), [Android Central: Fitbit Air India pricing](https://www.androidcentral.com/wearables/fitbit/fitbit-air-finally-lands-in-india-but-you-wont-like-the-pricing), [TechPP: Fitbit Air things to know](https://techpp.com/2026/10/14/fitbit-air-things-to-know/), [Android Authority: Google Health Premium price](https://www.androidauthority.com/google-health-premium-price-inclusions-features-3664507/)
- [Engadget: Health Guardian BP + insulin resistance](https://www.engadget.com/2235228/google-health-guardian-pixel-watch-5-blood-pressure-insulin-resistance/), [Engadget: unified Google Health app](https://www.engadget.com/2166841/google-unifies-health-fitness-apps-fitbit/), [Sahha: Health Guardian without FDA clearance (third party)](https://sahha.ai/blog/google-health-guardian-pixel-watch/), [Sahha: Google Health launch for developers](https://sahha.ai/blog/google-health-launch-2026/), [the5krunner: BP watch accuracy](https://the5krunner.com/2026/08/21/blood-pressure-watch-accuracy/), [Gadgets & Wearables: Health Guardian](https://gadgetsandwearables.com/2026/08/12/google-health-guardian-blood-pressure-insulin-resistance/)
- [TechRadar: Fitbit app becomes Google Health](https://www.techradar.com/health-fitness/fitness-apps/the-fitbit-app-is-finally-being-rebranded-as-google-health-here-are-5-things-you-need-to-know-about-the-big-change-and-what-it-means-for-fitbit-users), [Becker's: medical records sync](https://www.beckershospitalreview.com/healthcare-information-technology/disruptors/google-health-app-to-let-users-sync-medical-records/), [MobiHealthNews: Google × b.well](https://www.mobihealthnews.com/news/google-teams-bwell-connected-health), [T3: medical records in a fitness tracker](https://www.t3.com/active/fitness-trackers/fitbit-personal-health-coach-launch-0326)
- [Android Authority: Google Health two months later](https://www.androidauthority.com/google-health-app-two-months-later-3694569/), [Android Police: Gemini as health coach](https://www.androidpolice.com/i-let-gemini-track-meals-workouts-it-is-brilliant-health-coach/), [Eastern Herald: Fitbit Air review, AI coach worries](https://easternherald.com/2026/05/26/google-fitbit-air-review-ai-health-coach-problems/), [The Blaze: should you trust Google Health with your data](https://www.theblaze.com/tech/google-health-just-dropped-should-you-trust-it-with-your-data)
- [FoneArena: Pixel Watch 4 India price](https://www.fonearena.com/blog/462278/google-pixel-watch-4-price-india-features.html), [FoneArena: Pixel Watch 5 India price](https://www.fonearena.com/blog/489460/google-pixel-watch-5-price-india-features.html), [Gizmochina: Pixel Watch 4 India (LTE not in Indian model)](https://www.gizmochina.com/2025/08/20/google-pixel-watch-4-launched-india/), [Android Authority: Pixel Watch 4 satellite SOS](https://www.androidauthority.com/google-pixel-watch-4-satellite-connectivity-3588242/), [MediaNama: Jio × Google AI Pro 18 months free](https://www.medianama.com/2025/11/223-google-reliance-jio-free-ai-pro-plan-18-months/)

## 2026-10-23 — Samsung Health (Samsung Health app · Health Assistant beta · Galaxy Watch 9 / Ultra 2 · Galaxy Ring · Health Monitor · Xealth)

*Roster note: next unprofiled platform after Fitbit/Google Health. Research run 2026-10-23 from
Samsung's newsroom and mobile-press pages, plus Engadget, TechAdvisor, TechTimes, Digit, FoneArena,
Healthcare IT News and KS Post. Third-party-only figures are flagged.*

Samsung Health has about 77M monthly users (Samsung figure, quoted at VivaTech 2026). The app was
redesigned on 8 Jun 2026 around Sleep, Activity, Nutrition, Mindfulness and Vitals. Galaxy Watch 9 and
Watch Ultra 2 followed on 22 Jul 2026, alongside a US-only **Health Assistant** chatbot beta. **Main
finding:** Samsung is the strongest wearable rival *in India on regulated features*. Its
**CDSCO-cleared ECG and cuff-calibrated BP have been live in India since Jan 2024**, and it already
integrates **ABHA health records** (via Eka Care, Jan 2025). It also gives everything away free with
the hardware. Its gaps are a US-only AI, no labs, no bio-age, no risk models, and a July 2026 consent
row over AI training.

**Basic features.**
- **Vitals:** HR, HRV, SpO₂, respiration, skin temperature, sleep staging, and **Vitals**, an overnight
  baseline check over 7+ nights that flags deviations (wellness only).
- **Scores:**
  - **Energy Score:** daily readiness.
  - **Heart Health Score:** built from 7-day trends in sleep, stress, activity, body composition and
    BP. It replaced Vascular Load and arrived first on Watch 9 / One UI 9 Watch.
  - **Daily Cardio Load:** strain.
  - **Fitness Index:** VO2 max + BIA + steps, compared with peers.
- **Body composition:** BIA on the watch (body fat, skeletal muscle, water).
- **Nutrition and meds:** food logging with barcode scan; medication tracking and reminders (2024 US
  update).
- **Records:**
  - US: Health Records via b.well, covering labs, vitals, vaccines, prescriptions and visits.
  - **India:** ABHA creation in the app with Aadhaar or mobile number; an ABDM-certified locker
    (Eka Care) for prescriptions, labs and visits; and an OPD queue-token QR at ABDM hospitals.
    MediaNama raised multi-party data-sharing concerns.
- **Consults (US only):** "Find Care" via HealthTap, with same-day primary-care video and physician
  messaging.
- **Sleep extras:** Bedtime Guidance, which models sleep pressure and circadian rhythm from 3 nights;
  snoring detection on the phone.
- **Hardware in India:** Galaxy Watch 9 at ₹37,999 (40 mm Wi-Fi) to ₹44,999 (44 mm LTE) at launch.
  Street price is ₹34,999 on Amazon (Smartprix, Oct 2026). Deliveries started 7 Aug 2026.
- **Not found:** a consumer lab panel to buy, a bio-age score, Rx/GLP-1 prescribing, e-pharmacy, human
  coaches, or a caregiver health view.

**Advanced features.**
- **Health Monitor ECG + BP:** CDSCO-cleared in India (Jan 2024, Watch 4 and later). BP needs a cuff
  recalibration **every 28 days**. Both require a Galaxy phone. BP reached the US on 31 Mar 2026.
- **Sleep apnea:** FDA-cleared (2024), with an updated AI algorithm in Jul 2026. Needs 2 nights within
  10 days. For adults 18+ only, not for pregnant or already-diagnosed users. Select countries.
- **Antioxidant Index:** an optical skin-carotenoid reading from a fingertip on the watch, with trend
  history added in 2026. No other rival has this.
- **Health Assistant (beta, 21 Jul 2026):**
  - US only, opt-in, free.
  - Chat over the five data domains.
  - Samsung says its recommendations are "validated by physicians and certified health coaches"; the
    method is not described.
  - It does not diagnose or recommend treatment. Goal coaching is "planned".
  - The **model and whether it runs on device or in the cloud are not disclosed.**
- **Hearing:** unsafe-noise alerts and long-term hearing reports (Watch 9).
- **Fall detection:** sends SOS to emergency contacts; a third-party guide says it does not dial
  emergency services directly.
- **Clinical bridge (US):** **Xealth** (acquisition closed Oct 2025) connects 500+ US hospitals and 70+
  digital-health partners. Clinicians can order and monitor digital tools inside the EHR. Samsung says
  it is building toward doctors seeing watch data between visits.
- **Research:** a study with the MGH Diabetes Research Center (May 2026) uses Watch 8 BIA to track
  muscle loss in 100 adults starting GLP-1 drugs.
- **Ecosystem (announced, not shipped in app):** SiPhox (at-home bloods), Generation Lab (SystemAge
  bio-age; Samsung-backed), Lansik (glucose coaching), Natural Cycles, Calm, Bayer. A Generation Lab
  integration was announced via LinkedIn (TipRanks). I found no in-app launch.
- **CGM:** the app displays Dexcom data but Samsung sells no sensor. Non-invasive watch glucose is not
  shipped, and the FDA says no watch or ring is authorised for it. Galaxy Ring 2 reportedly comes no
  earlier than 2027 (single, weak source).

**Pricing.**
- **No subscription.** All Samsung Health features are free with a compatible Galaxy Watch or Ring. A
  rumoured ~$10/mo tier did not materialise (TechAdvisor). The hardware is the price: Watch 9 India
  ₹35k–45k.
- Many flagship features need a **Samsung phone** (ECG, BP, sleep apnea; the Heart Health Score needs a
  "compatible Galaxy phone"). The newest scores need Watch 7 or later on One UI 9 Watch.

**Weaknesses.**
- **The AI is US-only and opaque.** Health Assistant is a US beta with no stated model, grounding
  method or on-device status. Indian users get scores, not a coach.
- **Consent controversy (Jul 2026).** A new notice ties consent to "use of health data for AI training
  and modelling" to cloud sync. Declining, or withdrawing later, removes sync and deletes cloud copies,
  **including health records**, and allows human review. Samsung did not answer questions on
  anonymisation or retention (TechTimes, SamMobile). Region scope was unclear.
- **Lock-in.** The best features need a Samsung phone, which excludes iPhone users and many Indian
  Android users on Xiaomi, Vivo or OnePlus.
- **No labs, no bio-age, no trained risk.** The Heart Health Score is a wellness composite. BP needs a
  cuff every 28 days. The clinical loop (Xealth, HealthTap) is US-only.
- **App reliability.** User reports of sync errors, wrong-day data and crashes are mostly 2024–25
  community posts, so not current evidence.

**What Telomy should integrate.**
- *Core tech we can build:*
  1. **Take in Samsung data, not compete with the watch.** Read Samsung ECG/BP/BIA/sleep from Health
     Connect (Samsung Health writes to it; verify which types, since ECG may not be exposed). Feed **BIA
     skeletal muscle into the muscular-age clock** and BP readings into the hypertension/CVD risk
     model. Samsung measures these and does not turn them into an age or a 10-year risk.
  2. **A grounded AI for India first.** Samsung's assistant is US-only and discloses nothing.
     Telomy-LLX in English and Indian languages, every number tool-grounded, fills the gap Samsung leaves
     for every user outside the US.
  3. **Separate training consent from service.** Make model-training consent its own toggle that never
     touches sync or records. Our on-device LLM means we don't need user data to train the coach. This
     is a DPDP-aligned trust message that contrasts with Samsung (new matrix market-signal row).
  4. **Free cuff-less BP calibration reminders.** Samsung users already own a cuff and recalibrate
     every 28 days. Telomy can log the cuff readings as ground truth and calibrate our patch PTT
     against them.
- *Operational parity via partnership:* Samsung already does **ABHA records** in India through Eka
  Care, so ABHA is now **parity, not an opening** (matrix row updated). Use an ABDM integrator such as
  Eka Care for the same quick route. Labs remain the clear gap that Samsung also lacks: a Tata 1mg- or
  Thyrocare-style home collection partner makes Telomy "the blood test + risk + doctor layer on top of
  your Galaxy Watch".
- *Our opening:* in India Samsung has regulated sensors and records, but **no labs, no bio-age, no
  disease/mortality prediction, no doctor network and no AI coach**, and its best features are locked
  to Samsung phones. Pitch: "your Galaxy Watch measures; Telomy tells you what it means for your heart
  and lifespan, and books the doctor." **Watch item:** if Samsung ships the Generation Lab bio-age and
  SiPhox blood tests in-app, outside the US, it would close much of that gap at zero subscription cost.

Sources:
- [Samsung Mobile Press: Galaxy Watch Ultra2 and Watch9 health companions](https://www.samsungmobilepress.com/articles/new-galaxy-watch-ultra2-watch9-health-companions), [Samsung Mobile Press: Unpacked first look](https://www.samsungmobilepress.com/articles/galaxy-unpacked-2026-first-look-watch-ultra2-watch9), [Samsung Newsroom: next-gen Galaxy Watch features](https://news.samsung.com/global/samsung-introduces-next-gen-galaxy-watch-features-for-ai-powered-everyday-health-companion), [Samsung Newsroom: One UI 8 Watch features](https://news.samsung.com/global/new-features-on-one-ui-8-watch-help-users-build-healthier-habits), [Samsung Newsroom: VivaTech 2026 open ecosystem](https://news.samsung.com/global/samsung-highlights-open-ecosystem-to-accelerate-connected-care-for-daily-wellness-at-vivatech-2026), [Samsung Mobile Press: Medicare App Library recognition](https://samsungmobilepress.com/articles/samsung-health-connected-care-innovation-recognition-medicare-app-library-kill-the-clipboard)
- [Samsung Newsroom India: Health Records (ABHA)](https://news.samsung.com/in/samsung-introduces-personal-health-records-feature-on-samsung-health-app-in-india), [FoneArena: ABHA integration](https://www.fonearena.com/blog/444513/samsung-health-records-samsung-health-app-india.html), [MediaNama: ABHA data-sharing concerns](https://www.medianama.com/2025/01/223-samsung-integrates-ayushman-bharat-health-records-with-health-app-but-multi-party-data-sharing-sparks-concerns/), [Samsung Newsroom India: Health Monitor BP & ECG India debut](https://news.samsung.com/in/samsung-health-monitor-bp-ecg-tracking-on-galaxy-watch6-series-makes-india-debut), [Business Standard: BP/ECG in India](https://www.business-standard.com/technology/tech-news/samsung-brings-bp-ecg-monitoring-features-to-galaxy-watch-series-in-india-124011200533_1.html)
- [Engadget: Samsung Health Assistant](https://www.engadget.com/2219698/samsung-aims-to-help-you-make-more-sense-of-health-data-with-a-new-ai-powered-assistant/), [Fierce Healthcare: Health Assistant US beta](https://www.fiercehealthcare.com/ai-and-machine-learning/samsung-launches-beta-version-ai-powered-health-assistant-across-us), [HIT Consultant: Health Assistant + Xealth](https://hitconsultant.net/2026/07/21/samsung-launches-ai-health-assistant-beta-xealth-integration/), [TechAdvisor: Samsung Health overhaul](https://www.techadvisor.com/article/3157839/samsung-health-app-upgrade-announced-to-rival-google-health.html), [How-To Geek: Watch 9 health update](https://www.howtogeek.com/samsung-galaxy-watch-9-health-ai-coach/)
- [TechTimes: AI-training consent and record deletion](https://www.techtimes.com/articles/320412/20260714/samsung-health-deletes-medical-records-if-users-refuse-ai-training-before-galaxy-unpacked.htm), [Android Authority: Health Records, meds, food (2024)](https://www.androidauthority.com/samsung-health-app-update-health-records-medication-food-tracking-3492312/)
- [Healthcare IT News: Samsung acquires Xealth](https://www.healthcareitnews.com/news/samsung-acquires-xealth-push-toward-connected-care), [MobiHealthNews: Xealth finalised](https://www.mobihealthnews.com/news/samsung-electronics-finalizes-xealth-acquisition-digital-health-app), [KS Post: connected-care strategy at VivaTech 2026](https://www.kspost.biz/en-us/articles/2667), [HLTH: Samsung Health at HLTH 2025 (HealthTap Find Care)](https://hlth.com/insights/articles/samsung-health-at-hlth-2025-expanding-the-future-of-connected-care-2025-11-12), [TipRanks: Generation Lab × Samsung Health](https://www.tipranks.com/news/private-companies/generation-lab-plans-european-expansion-and-samsung-health-integration)
- [Digit: Watch 9 India launch](https://www.digit.in/news/wearable-devices/samsung-galaxy-watch-9-and-watch-ultra-2-launched-in-india-check-specs-price-availability-and-other-details.html), [TelecomTalk: Watch 9 India price](https://telecomtalk.info/samsung-galaxy-watch-9-launched-in-india/1009998/), [Smartprix: Watch 9 India price](https://www.smartprix.com/smartwatches/samsung-galaxy-watch-9-ppd154wv0pp6), [TechRepublic: Galaxy Watch glucose — what works](https://www.techrepublic.com/article/news-samsung-galaxy-watch-blood-sugar-tracking/), [Bill's Home Tech: Watch 9 guide (fall detection, third party)](https://billshometech.com/guides/samsung-galaxy-watch-9)
