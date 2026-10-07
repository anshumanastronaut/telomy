"""Narration and on-screen copy for the Telomy demo video. One entry per chapter (clips/<id>.mp4 is its screen recording)."""

CHAPTERS = [
    ("intro", "TELOMY", "Where human biology becomes intelligent",
     ["Member · Doctor · Longevity centre", "One Vault · Sinc AI · Clinician in the loop", "All data shown is fictitious test data"],
     "Telomy. Where human biology becomes intelligent. In the next few minutes we'll walk through the Telomy app as a member, as a doctor, "
     "and as a longevity-centre owner, and finish with how it's engineered. Everything you'll see uses fictitious test data."),
    ("roles", "01 · ONE APP, THREE ROLES", "Who's signing in?",
     ["Member, doctor or wellness-centre owner", "Each role gets its own home and tabs", "Switch any time from Profile"],
     "Telomy opens with a short brand moment, then asks who's signing in. One app serves three roles: a member managing their own health, "
     "a doctor, and a wellness-centre owner. Each gets its own home and navigation. We'll start as a member."),
    ("home", "02 · HOME", "Your biology, today",
     ["Longevity age — PhenoAge from 9 blood markers", "Every value carries its source and confidence", "HRV and sleep vs your own baseline",
      "Vault Rewind: see any past day"],
     "Home is the member's daily view. At the top is longevity age, biological age computed from nine routine blood markers with the published "
     "PhenoAge model, alongside pace of ageing and laboratory clocks. Every number carries a provenance chip: where it came from, when, and how "
     "confident we are. Below are today's heart-rate variability and sleep against the personal baseline, the next best action, and Vault Rewind, "
     "which shows the home screen exactly as it was on any past date."),
    ("vault", "03 · THE VAULT", "Every report, one record",
     ["24 report types: blood, gut, genetics, DEXA, CT, MRI, sleep, CGM, proteomics…", "PDFs parsed into 221 coded markers",
      "Sex-specific clinical zones and full history"],
     "The Vault holds everything: twenty-four report types, from blood panels and gut microbiome to DEXA, cardiac CT, MRI, sleep studies, "
     "continuous glucose and proteomic organ age. Reports are parsed straight from PDF into coded markers. Each marker is shown against "
     "sex-specific clinical zones, with its full history and what it connects to."),
    ("insight", "04 · SINC INSIGHTS", "Patterns, with receipts",
     ["Adjusted for confounders, checked for false discoveries", "Receipts: data, method, confidence, model version", "Clinician signs medical insights"],
     "Sinc, Telomy's AI, finds patterns across all of it, adjusted for confounders and checked for false discoveries. Every insight has receipts: "
     "the exact data, the method, the confidence interval and the model version. Medical insights stay drafts until a named clinician signs them, "
     "and the member can see that sign-off thread."),
    ("predict", "05 · DISEASE PREDICTION", "Validated models only",
     ["AHA PREVENT 2024 · Pooled Cohort Equations", "ADA diabetes · FIB-4 liver · KFRE kidney", "What-if levers recompute every model"],
     "Disease prediction uses validated equations only: the American Heart Association's 2024 PREVENT model, the Pooled Cohort Equations, "
     "the ADA diabetes score, FIB-4 for the liver and the kidney failure risk equation. The what-if levers recalculate every model live."),
    ("therapy", "06 · THERAPY", "What is actually working for you",
     ["Your centre and membership", "Health-span adaptability index", "Honest verdicts from your own sessions and nights"],
     "The Therapy tab is built for longevity centres. It shows the member's centre and membership, their health-span adaptability index, and, "
     "most importantly, what is actually working for them. Each therapy gets an honest verdict: working, promising, or no reliable signal, "
     "measured from their own sessions and the nights that follow."),
    ("cryo", "07 · INSIDE THE THERAPY", "Whole-body cryotherapy",
     ["What happens to the body, minute by minute", "Safety screened from the Vault", "Your response vs the published literature"],
     "Here's whole-body cryotherapy. Telomy explains what happens inside the body minute by minute, screens safety from the Vault, here coronary "
     "plaque on CT triggers a clinician check, and compares this member's measured response with the published literature."),
    ("session", "08 · INSIDE THE CHAMBER", "Minus 175 °C, second by second",
     ["Heart-rate surge, HRV collapse and rebound", "Skin temperature drop and rewarming", "Recovery constant k for every session"],
     "This is what happens inside the chamber at minus one hundred and seventy-five degrees. Heart rate surges, HRV collapses and skin "
     "temperature drops by sixteen degrees, then comes the parasympathetic rebound and rewarming. Telomy extracts the recovery constant and the "
     "rewarming time from every session. With machine telemetry and the Telomy patch, these traces become live measured data."),
    ("plan", "09 · THERAPY PLAN", "Built for your goal, signed by your doctor",
     ["Ranked by personal response, evidence and safety", "A weekly schedule with clear rules", "Nothing is booked until the doctor signs"],
     "From all of that, the member builds a therapy plan for a goal, here deeper sleep. Telomy ranks therapies by personal response, evidence "
     "and safety, lays out the week, and sends it to the doctor. Nothing is booked until the doctor signs."),
    ("tests", "10 · TESTS & SCANS", "What to test next, and why",
     ["75 tests with evidence grades, prep and prices", "Guideline screening + follow-ups + Vault gaps", "Tests without evidence are refused"],
     "Tests and scans: seventy-five tests with evidence grades, preparation and prices, plus a personal list, guideline screening for age and sex, "
     "the follow-ups the results call for, and gaps in the Vault. Tests without evidence are refused."),
    ("rx", "11 · TELOMY RX", "Supplements and medicines, doctor-certified",
     ["Triggered by data, never by a quiz", "Interaction checks against current medicines", "Doctor edits and signs the e-prescription"],
     "Supplements and medicines are triggered by data, not quizzes. Vitamin D is dosed from the measured level, and a statin conversation is raised "
     "by coronary calcium plus ApoB. Every item is checked for interactions, and the doctor edits and signs an e-prescription before anything "
     "can be ordered."),
    ("twin", "12 · DIGITAL TWIN", "A model of you that learns",
     ["Calibrated to how your body responds", "Ten-year what-ifs: heart risk, biological age", "Today, hour by hour · Mirror fidelity"],
     "The digital twin runs the member's life through published physiology, calibrated to how their own body responds. This member's vitamin D, "
     "for example, responds at only a fifth of the average. It projects ten years ahead under different choices, recalculating heart risk and "
     "biological age, simulates today hour by hour, and scores how well it mirrors reality. "
     "Today shows caffeine and, on a drinking day, blood alcohol through the evening, and predicts tonight's HRV and sleep. "
     "The mirror compares the twin with the member's real nights, and flags lab results that drifted more than their logged life explains: a missing input worth finding."),
    ("voice", "13 · TALK TO SINC", "Say anything, in any language",
     ["99 languages, including Hindi and Hinglish", "Meals, drinks, workouts, moods logged instantly", "Voice-stress features · audio never stored"],
     "Sinc listens in ninety-nine languages. Say anything, a meal, a drink, a cigarette, a workout, how you feel, and it's logged into the Vault. "
     "Voice tone becomes a stress signal compared with the member's own baseline, and raw audio is never stored."),
    ("life", "14 · ROUTINE · ACTIVITIES · ENVIRONMENT", "Your life, quantified",
     ["Describe a routine in plain words", "Track any activity: a bowler's spell, a golf round", "What your city's air and UV do to you"],
     "A routine can simply be described in plain words, and Telomy turns it into a schedule and quantifies it. Athletes can track any activity, "
     "a fast bowler's spell or a round of golf, with personal baselines. And the environment screen shows what a city's air and sunlight do to "
     "the body, comparing Delhi and Bengaluru."),
    ("membership", "15 · PLANS & CARE", "A doctor in the loop, every month",
     ["Free, Essential, Plus, Longevity Pro", "Doctor-signed monthly reports", "On-demand consultations"],
     "Membership plans include doctor-signed monthly reports and on-demand consultations, with a pre-clinic brief prepared for every visit."),
    ("doctor", "16 · FOR DOCTORS", "The day, prioritised",
     ["Patient panel ranked by risk", "AI summary first, then every report", "Same validated models as the member sees"],
     "Now the doctor. Their home shows the day's priorities, and the patient panel is ranked by risk using the same validated models. Opening a "
     "patient shows an AI summary first, then every report with its own summary, and which centre therapies are working. "
     "Each report opens with Sinc's draft: what is outside target, what changed since the last test, the findings that connect across reports, "
     "and suggested next steps and a re-test date. Every statement links back to a measured value, and it stays a draft until the doctor reviews it."),
    ("work", "17 · WORK QUEUE", "Everything waiting for a signature",
     ["Sinc drafts and monthly reports", "Consultations", "Therapy plans and prescriptions"],
     "The work queue collects everything waiting for a signature: Sinc drafts, monthly reports, consultations, therapy plans and prescriptions."),
    ("centre", "18 · FOR LONGEVITY CENTRES", "The live therapy floor",
     ["Revenue, utilisation and members", "Who is in which machine, right now", "In-session vitals, safety alerts, device status"],
     "Finally, the wellness centre. The dashboard tracks revenue, utilisation and members. The live therapy floor shows who is in which machine "
     "right now, with in-session vitals, safety alerts, and every device's status."),
    ("research", "19 · OUTCOMES & RESEARCH", "Every machine, every member",
     ["Outcomes for every therapy", "Response phenotypes across members", "The foundation for Telomy Labs"],
     "Across all members, Telomy reports outcomes for every therapy and clusters members into response phenotypes, the foundation of the "
     "research Telomy Labs will publish."),
    ("engineering", "20 · ENGINEERING", "How it's built",
     ["FastAPI backend · 171 endpoints · 45 tables", "117 automated tests on every push", "Expo React Native · local Whisper",
      "Validated clinical models · device API for machines and the patch"],
     "Under the hood: a Python FastAPI backend with a hundred and seventy-one endpoints, forty-five tables and a hundred and seventeen automated tests "
     "that run on every push. An Expo React Native app. Local Whisper for speech. Validated clinical models, and a device API for centre machines "
     "and the Telomy patch. Next come real device data, HealthKit, hosted infrastructure and TestFlight."),
    ("outro", "TELOMY", "Where human biology becomes intelligent", ["telomy.com"],
     "Telomy. Where human biology becomes intelligent. Thank you."),
]
CARDS = {"intro", "engineering", "outro"}  # full-frame cards (no phone)
