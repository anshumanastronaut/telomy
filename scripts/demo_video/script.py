"""Telomy demo + investor video — the frame-by-frame script.

One entry per frame: (id, label, title, bullets, voiceover, direction).
  • Screen frames show clips/<id>.mp4 (or <id>_1.mp4, <id>_2.mp4 … joined) beside the panel.
  • Card frames (CARDS) are full-screen typography — no phone.
  • Voiceover: record a human take per frame as voice/<id>.wav|m4a|mp3 (see docs/demo/RECORDING.md).
    Frames without a recording fall back to a macOS `say` scratch track so the cut can be reviewed early.

Facts used on cards, with sources:
  • ICMR-INDIAB (Lancet Diabetes & Endocrinology 2023): 101 M Indians with diabetes (11.4 %), 136 M with prediabetes (15.3 %).
  • Global longevity market ≈ US$26–35 B in 2025, ≈ US$66–74 B by 2034–35 (SNS Insider, MRFR, Spherical Insights, TrendX —
    estimates vary by scope; quote the range, not one number).
  • India health & wellness ≈ US$164 B in 2025 (IMARC).
  • B2B (med-spas, wellness centres, clinics) is the largest red-light-therapy revenue segment in 2025 (Hello Red Light market report);
    hyperbaric recovery chambers ≈ US$0.4 B in 2025, ~20 % CAGR to 2036 (openPR market release).
  • Prices are Telomy's own list prices in backend/app/plans.py.
Fill ASK before the final render. Nothing here claims customers or revenue — add real traction only when it exists.
"""

# ---- fill these before the final render (leave "" to show the neutral line) -------------------------------------------
ASK = ""          # e.g. "Raising ₹X Cr seed · 18 months runway"
USE_OF_FUNDS = ""  # e.g. "Patch v1 · 3 pilot centres · clinical validation"
CONTACT = "telomy.com"

CHAPTERS = [
    # ---------------------------------------------------------------- ACT 1 · THE PROBLEM (≈ 45 s)
    ("open", "", "More than 1 in 4 Indian adults has diabetes or prediabetes.",
     ["101 million with diabetes · 136 million with prediabetes", "ICMR-INDIAB, The Lancet Diabetes & Endocrinology, 2023"],
     "More than one in four Indian adults has diabetes or prediabetes. Most of them find out years too late. "
     "And the frustrating part is that the signs were usually there, in data they already had.",
     "Calm, unhurried. Let the number land. Pause one beat after 'too late'."),
    ("problem", "THE PROBLEM", "The data exists. Nobody connects it.",
     ["Lab reports sit as PDFs in WhatsApp", "Wearables track steps, not biology",
      "Centres run cryo, hyperbaric and red light, and measure almost nothing", "Doctors see one report, once a year"],
     "Blood reports sit as PDFs on a phone. The watch counts steps. Longevity centres are selling cryotherapy, hyperbaric oxygen and red light, "
     "but almost none of them measure what each session actually does to the person inside the machine. "
     "And the doctor sees one report, once a year.",
     "Slightly faster, list-like. Lean on 'actually does'."),
    ("intro", "TELOMY", "Where human biology becomes intelligent",
     ["One Vault for every report, wearable and session", "Sinc, an evidence-first AI", "A doctor signs every medical decision"],
     "Telomy fixes that. One Vault for every report, every wearable and every therapy session. "
     "An AI called Sinc that only says what the data can support. And a real doctor who signs every medical decision. "
     "Let me show you. Everything on screen is test data.",
     "Warm, confident, smiling voice. This is the turn of the story."),

    # ---------------------------------------------------------------- ACT 2 · THE PRODUCT (≈ 5 min)
    ("roles", "ONE APP, THREE CUSTOMERS", "Member, doctor, longevity centre",
     ["One app, three roles", "Each role gets its own home and tools", "The same data, seen from three sides"],
     "One app serves three customers: the member managing their health, the doctor who oversees them, and the longevity centre that treats them. "
     "We'll start as a member.",
     "Conversational. Quick, it's just orientation."),
    ("home", "MEMBER · HOME", "Your biology, today",
     ["Biological age from 9 routine blood markers", "Every number shows its source and confidence", "Today vs your own baseline, not a population average"],
     "This is home. At the top is biological age, calculated from nine routine blood markers with a published, peer-reviewed model. "
     "Every number tells you where it came from and how confident we are. Below that, last night's heart-rate variability and sleep, "
     "compared with this person's own baseline, not a population average. And one next action for today.",
     "Point at things with your voice: 'at the top', 'below that'. Steady pace."),
    ("vault", "MEMBER · VAULT", "Every report, one record",
     ["24 report types, from blood and gut to DEXA, CT and VO₂ max", "PDF in → 221 coded markers out", "Sex-specific zones and full history"],
     "The Vault takes twenty-four kinds of report: blood panels, gut microbiome, DEXA, cardiac CT, sleep studies, VO2 max, continuous glucose. "
     "You upload the PDF, and Telomy turns it into structured markers, each with its range, its history, and what it connects to.",
     "Brisk on the list, slow down on 'what it connects to'."),
    ("insight", "MEMBER · SINC INSIGHTS", "Patterns, with receipts",
     ["Adjusted for confounders and false discoveries", "Every insight shows its data, method and confidence", "Medical insights are signed by a clinician"],
     "Sinc finds patterns across everything: here, that coronary plaque is already present and ApoB is the lever that slows it. "
     "Every insight comes with receipts: the exact data, the statistics, the confidence. And anything medical stays a draft until a named doctor signs it.",
     "Serious and precise. 'Receipts' is a hook word, give it a little weight."),
    ("predict", "MEMBER · PREDICTION", "Validated risk models, with what-ifs",
     ["AHA PREVENT 2024 · ADA diabetes · FIB-4 liver · kidney failure equation", "Move a lever, every model recalculates"],
     "Risk prediction uses only validated clinical equations, including the American Heart Association's 2024 PREVENT model. "
     "And it's interactive: lower blood pressure or quit smoking, and every model recalculates in front of you.",
     "Show confidence. Slight excitement on 'in front of you'."),
    ("therapy", "MEMBER · THERAPY", "What is actually working for you",
     ["Every centre session, measured", "Honest verdicts: working, promising, or no signal", "From your own sessions and the nights after"],
     "Now the part that makes Telomy different. If you go to a longevity centre, Telomy tracks every session and the nights that follow, "
     "and gives each therapy an honest verdict. For this member, cryotherapy, sauna and PEMF measurably improved recovery. "
     "Red light and hydrogen? No reliable signal yet. We tell people that.",
     "This is the heart of the pitch. Slow down. Land 'We tell people that.' with quiet conviction."),
    ("cryo", "INSIDE THE THERAPY", "What happens to your body at minus 175",
     ["Minute-by-minute physiology", "Safety screened against your Vault", "Your response vs the published research"],
     "Tap a therapy and Telomy explains, minute by minute, what happens inside your body. It screens safety against your own records: "
     "here, coronary plaque on a CT scan means a doctor checks before the next cold session.",
     "Curious, explanatory tone."),
    ("session", "INSIDE THE CHAMBER", "Minus 175 °C, second by second",
     ["Heart-rate surge, HRV collapse, then rebound", "Skin temperature drops 16 °C, then rewarms", "A recovery score for every session"],
     "And this is a single session at minus one hundred and seventy-five degrees. Heart rate surges. HRV collapses, then rebounds. "
     "Skin temperature falls sixteen degrees and slowly rewarms. We turn that into a recovery score for every session, for every person. "
     "Today this is our physiology model. When the centre's machines and our patch stream live data, it becomes measurement.",
     "Almost documentary. Short sentences, a beat between each."),
    ("plan", "MEMBER · THERAPY PLAN", "Built for your goal, signed by your doctor",
     ["Ranked by your response, evidence and safety", "A weekly schedule", "Nothing is booked until the doctor signs"],
     "From that, a member builds a plan for a goal, say deeper sleep. Telomy ranks the therapies by what worked for them, the evidence and safety. "
     "It goes to the doctor, and nothing is booked until it's signed.",
     "Matter-of-fact."),
    ("tests", "MEMBER · TESTS", "What to test next, and why",
     ["75 tests with evidence grades and prices", "Guidelines + follow-ups + gaps in your Vault", "No evidence, no recommendation"],
     "Telomy also tells you what to test next, and why: guideline screening for your age and sex, follow-ups your results call for, "
     "and gaps in your record. If a test doesn't have evidence behind it, we won't recommend it.",
     "Firm on the last line."),
    ("rx", "MEMBER · TELOMY RX", "Supplements and medicines, doctor-certified",
     ["Triggered by measured data, never a quiz", "Checked against 130,000+ drug interactions", "Doctor edits and signs the e-prescription"],
     "Supplements and medicines come from data, not a quiz. Vitamin D is dosed from your measured level. "
     "Coronary calcium plus high ApoB raises a statin conversation. Every item is checked for interactions, "
     "and a doctor edits and signs the prescription before anything ships.",
     "Trustworthy, measured. This is also revenue, sound like you mean it."),
    ("twin", "MEMBER · DIGITAL TWIN", "A model of you that learns",
     ["Calibrated to how your body responds", "Ten-year what-ifs for heart risk and biological age", "Today, hour by hour · fidelity score"],
     "This is the digital twin: a model of the member, calibrated to how their body actually responds. "
     "This person absorbs vitamin D at a fifth of the average rate, and the twin knows that. "
     "It projects ten years ahead under different choices, simulates today hour by hour, from caffeine to alcohol, "
     "and every night it checks itself against reality. When the twin can't explain a change, it says so.",
     "Visionary but grounded. Smile slightly on 'the twin knows that'."),
    ("voice", "MEMBER · TALK TO SINC", "Say it in any language",
     ["99 languages, including Hindi and Hinglish", "Meals, workouts, moods, logged instantly", "Voice stress signal · audio never stored"],
     "Logging should be effortless, so Sinc listens in ninety-nine languages. Say it in Hindi, and the meal and the stress are logged. "
     "Say 'bowled six overs, fastest one thirty-four', and it lands in the bowler's training record. "
     "Your tone of voice becomes a stress signal, and the audio is never stored.",
     "Lighter, a little playful."),
    ("life", "MEMBER · LIFE", "Your routine, your sport, your city",
     ["Describe a routine in plain words", "Any sport, with personal baselines", "What your city's air and UV do to you"],
     "Describe your day in plain words and it becomes a schedule. Athletes create their own activity, a bowling spell or a round of golf, "
     "with personal baselines. And because where you live matters, Telomy shows what your city's air and sunlight do to you: "
     "the same person in Delhi breathes the equivalent of several more cigarettes a day than in Bengaluru.",
     "Relatable. The Delhi line should feel like a reveal."),
    ("membership", "MEMBER · PLANS & CARE", "A doctor in the loop, every month",
     ["Free · Essential ₹499 · Plus ₹1,499 · Pro ₹3,999 a month", "Doctor-signed monthly reports", "Consultations on demand"],
     "Members subscribe from four hundred and ninety-nine rupees a month, and on Plus and Pro, a doctor reviews and signs a report every month.",
     "Plain and clear. It's a business line, say it like one."),
    ("doctor", "FOR DOCTORS", "The day, prioritised",
     ["Patients ranked by validated risk", "AI summary first, then every report", "Which centre therapies are working"],
     "Now the doctor's side. Patients are ranked by risk, using the same validated models. "
     "Open a patient and you get the AI summary first: what's out of range, what changed, what connects across reports, "
     "and which centre therapies are working. Then every report, each with its own summary. "
     "Every sentence links back to a measured value, and stays a draft until the doctor approves it. "
     "That's how one doctor can look after hundreds of members properly.",
     "Respectful, peer-to-peer, as if talking to a clinician. Land the last line."),
    ("work", "FOR DOCTORS · WORK QUEUE", "Everything waiting for a signature",
     ["Monthly reports and Sinc drafts", "Therapy plans", "Prescriptions and supplements"],
     "Everything waiting for a signature lives in one queue: monthly reports, Sinc's drafts, therapy plans and prescriptions.",
     "Brisk."),
    ("centre", "FOR LONGEVITY CENTRES", "The live therapy floor",
     ["Revenue, utilisation and members", "Who is in which machine, right now", "In-session vitals, safety alerts, device status"],
     "And the longevity centre. The owner sees revenue, utilisation and members. "
     "The live floor shows who is in which machine right now, with their vitals and safety status, and every machine's service schedule.",
     "Operational, confident. Imagine you're talking to a centre owner."),
    ("research", "FOR CENTRES · OUTCOMES", "Every machine, every member",
     ["Outcomes for every therapy", "Members grouped by how they respond", "The foundation for Telomy Labs"],
     "Across all members, Telomy groups people by how they respond: fast rebounders, typical, slow rewarmers. "
     "Very few centres anywhere have this kind of data today. It's the start of our own research arm.",
     "Slow, a little awe. Say the second sentence plainly."),

    # ---------------------------------------------------------------- ACT 3 · THE BUSINESS (≈ 1 min 45 s)
    ("whynow", "WHY NOW", "Three shifts, at the same time",
     ["Centres are adding cryo, hyperbaric and red light, and need proof",
      "Continuous sensors are cheap; lab tests are routine", "AI can now explain biology, if it's grounded and supervised"],
     "Why now? Three things are happening at once. Longevity centres are installing cryo, hyperbaric and red-light machines, "
     "and their customers are starting to ask for proof. Sensors and lab tests have become cheap and routine. "
     "And AI can finally explain biology, as long as it's grounded in real data and supervised by a doctor. That's exactly what we built.",
     "Founder voice. Count the three on your fingers as you speak, it changes how you sound."),
    ("market", "MARKET", "A large market, and a clear wedge",
     ["Global longevity market ≈ US$26–35 B (2025) → US$66–74 B by 2035",
      "India health & wellness ≈ US$164 B (2025)",
      "Clinics and wellness centres are the largest buyers of red-light therapy"],
     "The global longevity market is estimated at around thirty billion dollars today, and expected to more than double within ten years. "
     "India's health and wellness market is already over one hundred and sixty billion. "
     "Our wedge is the longevity centre: the place where people already pay for these therapies, and where outcomes are rarely measured.",
     "Numbers clearly, not rushed. 'Our wedge' is the important bit."),
    ("model", "BUSINESS MODEL", "Three revenue lines, one platform",
     ["Centres: ₹14,999–39,999 / month SaaS", "Members: ₹499–3,999 / month plans", "Telomy Rx and diagnostics, doctor-certified"],
     "We make money three ways. Centres pay a monthly subscription to run their floor and outcomes on Telomy. "
     "Members subscribe for their Vault, Sinc and their doctor. And Telomy Rx and diagnostics, always doctor-certified, add revenue on top. "
     "Every centre we sign brings its members with it.",
     "Crisp. The last sentence is the flywheel, give it weight."),
    ("moat", "WHY TELOMY WINS", "A dataset almost nobody is collecting",
     ["Session-level physiology for every machine and member", "Physiology models validated against the literature",
      "Doctor-in-the-loop safety from day one", "Built for India: Hindi, Hinglish, Indian labs, Indian cities"],
     "Why us? Every session on every machine builds a dataset almost nobody is collecting: how real people respond to cryo, heat, "
     "pressure and light. Our physiology models are already validated against the published research. Doctors are in the loop from day one. "
     "And it's built for India: our languages, our labs, our cities.",
     "Proud but not arrogant."),
    ("engineering", "ENGINEERING", "Built, tested and running",
     ["Python FastAPI backend · 171 endpoints · 45 tables", "117 automated tests on every push", "React Native app for iOS and Android",
      "Device API ready for centre machines and the Telomy patch"],
     "This isn't a mock-up. It's a working platform: a Python backend with a hundred and seventy-one endpoints and a hundred and seventeen "
     "automated tests, a React Native app for iPhone and Android, speech recognition that runs locally, and a device API that is ready for "
     "the centre's machines and our own patch, which is in development now.",
     "Engineer's pride. Steady and specific."),
    ("ask", "WHAT'S NEXT", "From prototype to the first centres",
     ["Next: live machine data, the Telomy patch, pilot centres", "Then: clinical validation and the first Telomy Labs study"],
     "Next, we connect live machine data, ship the patch, and launch with our first pilot centres. "
     "If you'd like to be part of building the operating system for longevity, we'd love to talk.",
     "Direct, warm, look into the lens if you're on camera. Slow down on the final sentence."),
    ("outro", "TELOMY", "Where human biology becomes intelligent", [CONTACT],
     "Telomy. Where human biology becomes intelligent.",
     "Quiet and slow. Let it breathe."),
]

CARDS = {"open", "problem", "intro", "whynow", "market", "model", "moat", "engineering", "ask", "outro"}

# fill the ask card from the variables above
for i, row in enumerate(CHAPTERS):
    if row[0] == "ask" and (ASK or USE_OF_FUNDS):
        CHAPTERS[i] = (row[0], row[1], row[2], [x for x in (ASK, USE_OF_FUNDS) if x] + row[3], row[4], row[5])
