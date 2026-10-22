# Telomy Proactive Check-in Engine — trust-first JITAI prompts

`telomy-slm/telomy_llx/checkin_engine.py`. Decides when/what to ask you during the day, grounded in
JITAI / EMA / notification-fatigue research. Principles: (1) receptivity gate first — never prompt in
quiet hours, within the min gap, over the daily cap, or when driving/sleeping/busy/in-session/snoozed;
(2) event-triggered (voice arousal, RHR/HRV spike, sedentary, symptom mention, protocol due) over random
nagging + a little rate-limited mood/hydration EMA; (3) SELF-TUNING confidence — each prompt type tracks
precision (did you confirm it useful?) + overall response-rate; low-confidence triggers get a higher bar,
a falling response-rate cuts frequency (the trust/confidence factor — it earns the right to interrupt);
(4) user control + transparency — ~3/day default, adjustable quiet hours/frequency, snooze, a "why" on
every prompt. Safety prompts (symptom follow-up) bypass tuning but stay receptivity-gated. Returns the
decision; the app delivers on-device. Pairs with personal_agent daily_summary for the evening audit.
