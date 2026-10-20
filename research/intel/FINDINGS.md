# Telomy Research-Intelligence — Findings Log

Append-only. Each dated entry: theme · key findings (with source URLs) · datasets/models/companies
discovered · **Standout opportunities for Telomy**. Seeded below with the initial model-area sweep.

---

## 2026-10-20 — Seed sweep: acute-cardiac, fall, emergency & long-term multiparameter models

**Heart attack (acute MI) from wearable ECG/PPG.** Single-lead deep-learning MI classifiers report
~97% F1 on curated PhysioNet-style data, but **ST-segment sensitivity is poor (8–12%)** and there is
**no prospective wearable validation** for acute MI. Arrhythmia (AF) detection from PPG/single-lead is
far more mature (~95%). PPG foundation models are emerging (AnyPPG, >100k hours).
→ *Honest stance:* do NOT claim acute-MI event detection. Target AF + arrhythmia + structural-HD risk
+ MI *risk*, clinician-in-the-loop.

**Fall detection.** SisFall lab accuracy ~97–98%, but **real-world false alarms are the hard problem**
(>1/hour on real daily-life data; sitting-down-hard is the classic false trigger). Pre-impact detection
(~260 ms lead) demonstrated. Datasets: SisFall, KFall, MobiFall, and FARSEEING (real falls).
→ Report false-alarms/day, validate on real falls, use a confirmation window.

**Emergency SOS design (Apple pattern).** Detect → wrist tap + alarm + alert → **countdown/confirmation
window** → auto-call only after ~1 min immobility → notify emergency contacts with location. False
positives from rapid-motion-then-stop (skiing, rollercoasters). Lesson: confirmation window + immobility
gate + easy user override are essential; neck/waist placement detects falls better than wrist.

**Long-term multiparameter prediction.** Wearable HRV predicts major adverse cardiovascular events in
healthy middle-aged adults; a transformer fusing HRV + sleep + SpO2 + steps predicted post-PCI
inflammation (AUC 0.88); HRV time-series foundation models (zero-shot forecasting) are new. No clean
AF/diabetes-from-continuous-wearable benchmark found yet.
→ Telomy edge: we already collect ring PPG + patch ECG (HRV, arrhythmia) + SpO2 — fuse with the blood
clocks + disease models for a multimodal risk engine no one has at consumer scale.

Sources: bioengineering wearable-ECG primer; AnyPPG (arXiv 2511.01747); PLOS ONE PPG CNN; SisFall
ensemble (ScienceDirect 2025); cross-dataset real-fall study (ScienceDirect); Apple Fall Detection
support docs; Frontiers HRV review 2025; wearable biomarkers DTx review (Bioengineering 2025).

## 2026-10-21 — Theme 1: Competitive landscape (longevity / aging-clock / digital-health)

- **Function Health is the US scale leader.** It raised a $298M Series B at a $2.5B valuation (Nov 2025, Redpoint and a16z), cut its price to about $365/yr, bought Ezra (AI full-body MRI) in May 2025, and is building a doctor-trained "Medical Intelligence" generative model on member data. In Jul 2026 it reportedly took $450M of non-dilutive, revenue-linked capital from General Catalyst's Customer Value Fund. The $450M figure comes from a VC blog, so verify it. https://www.fiercehealthcare.com/health-tech/function-health-lands-298m-series-b-rolls-out-medical-intelligence-ai-model-health-data · https://athletechnews.com/function-health-raises-298-million-at-2-5-billion-valuation/ · https://valueaddvc.com/blog/function-health-450m-financing-2026-why-valuation-stayed-at-2-5b
- **Blood-panel subscriptions are now a commodity.** Superpower sells 100+ biomarkers with a bio-age score for $199–349/yr (sources disagree). InsideTracker charges $99 extra for InnerAge. The "biological age" these products report is a proprietary blood-marker algorithm with no published validation. The market is put at $3.31B in 2026 and $5.58B by 2030; that is a paid market-research press release, so treat it as hype-grade. https://superpower.com/biomarker-testing-companies/function-health-vs-insidetracker · https://www.globenewswire.com/news-release/2026/09/03/3356030/28124/en/
- **Wearable makers are converging on labs plus a bio-age score.** WHOOP launched Advanced Labs (65 markers via Quest) in Sep 2025, added free upload of any lab report (PDF or screenshot, any language), and in Apr 2026 added $299 specialty panels (75–89 markers). Its "WHOOP Age / Pace of Aging" is explicitly wellness-only. Oura reportedly launched "Health Panels" (up to 50 markers); I only found that in one secondary source. https://www.businesswire.com/news/home/20250930178710/en/ · https://longevity.technology/news/whoop-adds-free-lab-test-uploads-for-all-users/ · https://www.whoop.com/us/en/press-center/whoop-launches-specialized-panels-to-deliver-deeper-more-personalized-health-insights/
- **Ultrahuman is the most direct India rival.** Blood Vision runs through Tata 1mg phlebotomy across 60+ cities and 2,000+ PIN codes. India pricing is ₹999 entry, ₹1,999 Base (60+ markers) and a Premium tier (100+). Its free **Vision Cloud** takes a report from any lab and returns a "Blood Age" plus supplement suggestions, much like Telomy's upload-and-interpret flow. It is also opening physical health centres. https://www.businessworld.in/article/ultrahuman-blood-vision-vision-cloud-india-launch-preventive-health-578952 · https://www.outlookbusiness.com/deeptech/tech/ultrahuman-partners-with-tata-1mg-to-further-expand-its-blood-vision-service-to-over-60-cities-across-the-country
- **The rest of the India longevity field is small and clinic-led.** Biopeak (Bengaluru, ~$11M total, Nikhil Kamath), Decode Age ($1.7M raised Dec 2025, about ₹15 Cr FY25 revenue, mostly supplements), VytalYou (₹9 Cr raised at ~₹33 Cr valuation, Mumbai centre), Nura (82k+ AI screenings) and DeAge are all clinics or supplement brands. Dr Dangs Lab sells TruAge methylation testing. Commentators flag that the sector is "largely unregulated" and has a business-model problem: people pay before they are patients. https://openthemagazine.com/india/longevity-inc-india-joins-the-immortality-race · https://startupchai.substack.com/p/indias-longevity-boom-has-a-business · https://longevity.technology/news/decode-age-advances-longevity-pipeline-after-1-7m-raise/
- **Mass-market Indian labs own logistics but not intelligence.** Redcliffe claims 7M+ customers, and Tata 1mg reaches 1,900+ cities with "Smart Reports" that show trends. Neither offers validated aging clocks, wearable fusion, or a clinician workspace. I found nothing on Healthians in this pass. https://www.similarweb.com/app/google/com.redcliffelabs/bulgaria/
- **Epigenetic clocks are consolidating but still have weak evidence.** Infinite Epigenetics acquired Tally Health (Apr 2026). For TruDiagnostic, GlycanAge and Generation Lab, no clock has FDA PMA, De Novo or 510(k) authorization, and estimates differ by several years across algorithms. Most published criticism comes from rival vendors, which is a conflict of interest. Several consumer tests feed chronological age into the model, which inflates how accurate they look. https://knowyourdna.com/trudiagnostic-review/ · https://outliyr.com/biological-age-test-comparison · https://www.forbes.com/sites/josipamajic/2026/02/20/the-biological-age-testing-market-from-research-promise-to-clinical-reality/
- **India's research infrastructure is emerging.** IISc published the protocol for the **BHARAT Study** (Apr 2026), described as India's first large-scale multi-omics aging cohort. It is a likely partner or validation-data source. https://openthemagazine.com/india/longevity-inc-india-joins-the-immortality-race

**Datasets / models / companies discovered**
- Companies: Function Health (+Ezra), Superpower, InsideTracker, WHOOP Advanced Labs/Healthspan, Oura Health Panels, Ultrahuman Blood Vision + Vision Cloud, Tata 1mg, Redcliffe Labs, TruDiagnostic, GlycanAge, Generation Lab (SystemAge), Infinite Epigenetics/Tally Health, Biopeak, Decode Age, VytalYou, Nura, DeAge, Dr Dangs Lab (TruAge India).
- Models: Function "Medical Intelligence Lab" generative model (proprietary); WHOOP Age / Pace of Aging (white paper: https://www.whoop.com/us/en/thelocker/Healthspan-Data-Meets-Longevity/).
- Datasets/cohorts: BHARAT Study (IISc multi-omics aging cohort, protocol Apr 2026; access terms to be found on Day 2).

**Standout opportunities for Telomy:** (1) **Publish our numbers.** No rival, US or Indian, publishes MAE, C-index or calibration for its "blood age". If we release a validation note for our NHANES clocks (MAE, mortality C-index, a test on Indian samples) and show the "without chronological age as input" variant, scientific honesty becomes our moat against Ultrahuman Vision Cloud and WHOOP. (2) **Own the clinician and centre layer.** Every competitor sells straight to consumers. Our multi-role platform (doctor/centre/super-admin workspaces, care graph) can be the white-label intelligence layer for Redcliffe, Tata 1mg-style labs and the new longevity clinics (VytalYou, Nura, Biopeak). These players have logistics and footfall but no validated clocks, wearable fusion or explainable SLM. A B2B2C deal avoids competing with Ultrahuman on hardware and marketing spend. (3) **Fuse wearables with labs, India-calibrated.** WHOOP and Oura bolt labs onto their own wearables, and Ultrahuman's India labs are not tied to ECG patch data. Telomy can combine ring PPG, patch ECG/HRV/SpO2, blood clocks and IFCT-based nutrition, with reference ranges calibrated to Indian populations. (4) **Pursue a BHARAT Study / IISc partnership** early. External validation on Indian data is something no rival can currently claim. Caveat: Ultrahuman's free upload-and-interpret tool already matches our basic feature, so free upload alone is not a differentiator.
