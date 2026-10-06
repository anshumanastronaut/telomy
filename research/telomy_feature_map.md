# Telomy app — feature map (Nostavia parity + Telomy USPs)

Source inputs: `nostavia_teardown.md` (live teardown + dummy-lab test, 2026-10-06), Telomy 10 App Features, 10 Features To Build Next, 10 USPs, Engineering Guide v3.0, UI Design System v1.0.

Rule: copy **capabilities and flows**, never Nostavia's code, copy, visual design or brand. Telomy's look follows UI Design System v1.0 (Cloud Dancer / Ink, teal = science, copper = human, Inter + display serif, 1px charts, no gradients, no gamification).

## Navigation (Design System §8.1)
Bottom tabs: **Home · Vault · Sinc · Sessions · Profile**. Capture sheet ("Log") opened from Home quick actions and the Vault header (replaces Nostavia's "+" FAB).

## Parity map
| Nostavia feature | Telomy treatment |
|---|---|
| Home hero (Bio age/VO2/HRV/Energy/Steps switcher, info sheet) | Longevity-age **dial** (chronological tick, copper/graphite fill, confidence %, "How this is calculated"), metric switcher kept; every value has a **provenance chip** + **confidence gradient** |
| Quick actions (Diet plan, Log meal, Ask AI, Meditate) | Log event · Log meal · Ask Sinc · Breathe (session) |
| Daily Blueprint checklist | **Today's protocol** checklist (clinician-authored, from active protocol) |
| Food / Cardio / Performance intelligence cards + detail pages (4 weighted pillars, clinical ref, signal feed) | Domain cards (Metabolic, Cardiovascular, Recovery) → detail with pillars, **Open Methods** sheet (formula, citations, model version, inputs used/missing), signal feed with n + freshness caption; missing inputs shown as "not available", score re-weighted & confidence lowered |
| Leagues / XP / coins | **Not built** (design system forbids). Replaced by **Vault Completeness %** with concrete next steps |
| Protocol tab (phase, pillars, weekly Indian menu + AI swap, protocol library, disclaimer) | Sessions tab → Protocol (pillars, clinician name, review cadence), Weekly menu with swap, **Protocol Marketplace** (clinician-authored, evidence rating, clinician review before activation) |
| Labs tab (panel switcher 6 panels, summary, search, filters, marker expand + AI summary + deep dive, upload → AI extraction → verify) | Vault → Biomarkers: same 6 panels with **correct routing**, multi-report history with **true per-date values**, report's own reference range kept, provenance "lab · date", upload → parse → verify → save, genotype shown as variant not "outlier" |
| Bio-age report doesn't update hero | Bio-age panel feeds the dial (PhenoAge default, DunedinPACE → pace) |
| AI chat (history, regenerate, attachments, feedback) | **Sinc** chat: cites evidence chips, confidence, "Awaiting clinician review" on medical-adjacent replies, "Draft for my clinician", visible errors + retry, history |
| Meal logging (camera/gallery/voice/describe) + 13-section meal analysis | Log meal (describe/photo/voice) → analysis with score, macros, circadian timing, glucose-response estimate — each section carries confidence + "correlates with" language |
| Nutrition trends | Vault → Nutrition trends (7-day bars vs target) |
| Wearables live tracking (rings, strain/recovery/sleep, stress, vitals grid, cardio, heatmap) | Vault → Signals: same vitals with provenance ("ring · synced 2h"), never fabricate when no data |
| Meditation timer + stats | Sessions → Breathe/meditate timer + history (no streak flames) |
| Book doctor hub (specialists, consult types, slots, appointments) | Profile → **Clinicians**: panel + booking (clinic / video / home lab), appointments, + **Pre-clinic brief** button per appointment |
| Shop | **Formulas** (clinician-recommended supplements only) inside Marketplace |
| Export health PDF | **Specialist Pack Generator** (cardiologist / gynaecologist / psychiatrist / dentist / GP) — FHIR-shaped JSON + print-ready PDF, provenance per value, no sample data |
| Settings (goals, assessment, notifications, connections, AI memories, module order, icon, legal, delete) | Profile: Goals, Baseline assessment, Connections, Sinc memory (view/delete facts), Notifications, Consents, Data export, Legal, Delete account |
| Onboarding 6 pages + single consent checkbox | Onboarding per DS §10.7: name + phone OTP → connect wearable (skippable) → **per-purpose consent toggles (default off)** → starter goal → meet Sinc |

## Telomy-only features (USPs) in this build
1. Provenance chip on every number (source · time · confidence) + long-press provenance card.
2. Confidence gradient (saturation by evidence count).
3. Receipts button on every insight (data points, window, model version, CI).
4. Live clinician sign-off thread (drafted → awaiting Dr. X → signed/modified/rejected) — with a minimal Telomy Care web page for the clinician to act.
5. One-tap N-of-1 launcher (log supplement → "Run as a study?" → ABAB schedule → readout Helped / No reliable signal / Possible negative).
6. Vault Rewind (date slider rewinds Home).
7. Life-event overlay on charts + Daily reflection.
8. Family Vault (scoped, time-boxed, revocable sharing + access log).
9. Pre-clinic / specialist brief generator (PDF + FHIR JSON).
10. Protocol Marketplace (clinician-authored).
11. Research contribution dashboard (preprints; research consent).
12. Vault completeness score.
13. DICOM studio (imaging studies with series/slice scrubber + parsed radiologist findings).
14. Pending-clinician queue for solo users (request one-time review).
15. DPDP per-purpose consent centre + consent history.
16. Cross-report correlation engine (backend) — finds lab↔lab, lab↔genetics, lab↔wearable, event→biomarker patterns with evidence counts and confidence.
