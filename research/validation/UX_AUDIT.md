# Conscious UX audit — full platform lifecycle sim (user ↔ doctor ↔ centre)

Driven end-to-end on the local multi-role backend: member **Riya Sim**, doctor **Dr. Sim Rao**, centre
**Bengaluru Longevity Clinic**. The platform is **logically complete** — every lifecycle stage works:
onboarding, doctor/centre allocation, clinical note + sign, n-of-1 trial, centre enroll + book + check-in +
complete, supplement **order → confirmed → packed → dispatched → in_transit → delivered**, billing cycle, and
the member sees it flow back (meds, therapies, reports, **reminders** like "Dr. signed a Sinc draft").

## ADD (to make the experience better)

1. **Address book** — HIGH. Orders carry an `address` string but the member has no saved-addresses UI. Home
   care + medicine/supplement delivery need Home/Work/Parents addresses with a default. Build `/addresses`.
2. **Payment methods & gateway choice** — HIGH. Billing supports gateways (razorpay) and subscriptions, but the
   member has no "Payment methods" screen (saved UPI/card, default, choose at checkout). Build `/payment-methods`
   and surface gateway choice in subscribe/checkout.
3. **Emergency & home care** — DONE (this session): ambulance one-tap + home nursing, elder/old-age care, baby &
   child care, physio-at-home, lab pickup, medicine delivery, caregiver. Next: route requests into the centre's
   orders queue (not just the Vault) so they're fulfilled + tracked.
4. **A member "Orders & requests" tracker** — MEDIUM. Deliveries, home-care requests and bookings exist
   server-side but the member has no single place to see status (packed/dispatched/delivered, booking times).
5. **Recovery fallback to daily signals** — MEDIUM. The Today Recovery card shows "No night yet" even when daily
   RHR/HRV/sleep signals exist (it only reads WHOOP raw-night data). Fall back to the daily signals, or clearly
   say "wear a device overnight for recovery."

## FIX (bugs/scoping found in the sim)

- **Doctor panel shows ALL 140 seed patients**, not just the doctor's assigned care-graph panel. A doctor must
  see only their panel (`/mgmt/doctor/patients` should scope by care_edges/doctor_id). HIGH.
- **Care-graph `people` vs centre `members` (enrollment) are two separate concepts** — assigning a patient to a
  centre does not make them a centre "member". Decide: auto-create a member on centre assignment, or clarify the
  distinction in the UI. MEDIUM.
- (Fixed this session) user_ref email → user DB resolution; doctor patient detail; Apple Health on Android;
  patient-card navigation; nav bar; sign-in keyboard; timeline/circadian.

## REMOVE / SIMPLIFY

- **The You tab is very dense** — 6 groups, ~25 rows. Consider grouping under fewer top-level entries (e.g.
  "Care & services", "My data & settings") with detail inside; the current wall of rows is a friction.
- **Role doesn't persist across cold start** — the app returns to role-select every launch; it should remember
  the last role (members especially should never re-pick).
- **Staff token is shared** — logging in as centre logs out the doctor (one staff session). Fine if a person is
  one role; friction for someone who is both.

## Engines (validated clean)

Organ clocks (age-calibrated), Vault risk map (5/5), longevity Rx + macros (7/7, claims firewall + renal gate),
chronic-risk ML (strong discrimination). All behave logically and show the right data.
