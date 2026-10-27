# Telomy Console — Design direction

**Who & where:** two web workspaces on one system — a **Centre console** (front desk, managers, therapists) and a
**Doctor console** (clinicians) — used on desktop at a desk and on a tablet on the floor.

**Feeling:** calm clinical-premium. Trustworthy, quiet, data-dense but never cluttered. Closer to Linear/Stripe
dashboards than a consumer app. Confidence through restraint.

**Direction (from real products):** Stripe Dashboard (data density + calm), Linear (speed, keyboard, crisp type),
Oura/WHOOP web (health warmth). Not flashy; legible first.

## Tokens
- **Colour:** ink `#0f1613`; surface `#ffffff` / `#f6f8f7`; primary deep green `#137a5f` (Telomy), hover `#0f5c47`;
  copper accent `#c9792f` for attention; status green/amber/red; neutral border `#e4eae7`. Dark mode mirrors these.
- **Type:** Inter (system fallback). Scale 12/13/14/16/20/28/36. Numbers tabular. Tight tracking on headings.
- **Space:** 4px base; cards 16–20px padding, 12px radius; generous section gaps; max content 1200px.
- **Depth:** one soft shadow for cards; 1px borders do most of the work.
- **Motion:** 120–180ms ease-out; nothing bouncy.

## Layout
- Left sidebar (collapsible) with workspace switch (Centre ⇄ Doctor) + module nav; top bar with org/branding + search.
- Content = cards and tables. KPI row at the top of each dashboard. Right-side drawer for create/edit (never full-page).
- Fully responsive: sidebar collapses to icons < 1024px, becomes a top sheet < 640px; tables scroll.

## Principles
- **Modular:** nav + forms are driven by the backend (`/mgmt/overview`, `/mgmt/form`) — a new therapy/field/module
  appears automatically. Disabled modules don't render.
- **Trust:** every number shows its source/time; medical actions are clearly gated; nothing invented.
- **Fast:** keyboard-first, optimistic where safe, skeletons not spinners.

## Clinical decision-support patterns (Longevity Rx view)
Grounded in CDS/EHR UX research (alert-fatigue reviews; clinician preference for colour-coded risk + graphs+tables; inline over interruptive):
- **Tiered, passive, never a pop-up.** Recommendations group into Foundation → Clinical → Optional → Experimental and render inline. Interruptive alerts cause fatigue; we surface, we don't nag.
- **One evidence-grade chip, consistent everywhere.** `A` green (ok) · `B` teal (primary) · `C` copper (warn) · `D` grey (faint). The grade is always paired with its *scope* (what the grade is for — usually a biomarker, never "lifespan").
- **Rationale on demand.** Each item has a `<details>` "Why & evidence" — the reasoning is one click away, not shouting on the card. Reduces cognitive load.
- **Safety is data-backed and visible.** FAERS disproportionality signals (ROR + 95% CI, from ~20.7M reports) show as chips on drugs — a watchlist, not a block. Hard contraindications/interactions show as red badges; Rx-gated items are badged.
- **Source + gate on everything.** Every number carries its basis; medical items are clearly prescriber-gated; a clinician sign-off step closes the view. Nothing invented.
- Mirror of these tokens/patterns lives in `web/console` (identical copy); the deployed console is `backend/webconsole`.
