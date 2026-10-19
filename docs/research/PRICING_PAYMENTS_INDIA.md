# Pricing & Payments — India Wellness/Longevity Market

**Status:** research → implemented in `backend/app/billing.py` · **Updated:** 2026-10-19

Grounding for Telomy's pricing, packages and payment-gateway model. Figures are from public commentary
(no Indian longevity clinic publishes a full rate card), so they are **indicative** and tunable per centre
in the catalog — nothing here is hard-coded into logic.

## Market signal
- **Premium membership** (e.g. "Longevity Inc." style): ~₹1,00,000 / month — unlimited consults, therapies,
  a set number of IV drips, diagnostics, dietitian. Members typically stay 12–18 months.
- **Core annual membership:** ~₹1.5L–₹3L / year (blog blueprint).
- **Initial longevity assessment** (90–130+ biomarkers ± DEXA/VO2): ₹25,000 – ₹1,00,000+.
- **Standard executive health check:** ₹3,000 – ₹5,000.
- India has few dedicated longevity clinics; EHC packages are the common entry product.

## Telomy plan ladder (implemented)
**Memberships (recurring, via mandate):**
| Plan | Price | Cycle | Credits | Notes |
|------|-------|-------|---------|-------|
| Core Longevity (Monthly) | ₹12,999 | 30d | 4 | Quarterly panel, 2 consults/mo, dietitian |
| Core Longevity (Annual) | ₹1,29,999 | 365d | 48 | ~2 months free, annual DEXA+VO2 |
| Plus Longevity (Monthly) | ₹24,999 | 30d | 8 | Monthly consults, 1 IV/mo, quarterly DEXA, 130+ panel/qtr |
| Elite Longevity (Monthly) | ₹99,999 | 30d | ∞ | Dedicated physician, unlimited, monthly panel+imaging |

**One-time assessment packages** (booked & billed as services):
Essential Health Check ₹4,999 · Longevity Assessment ₹24,999 · Comprehensive Longevity Panel ₹49,999 · Executive 360 ₹89,999.

**À-la-carte** therapies/diagnostics: sauna ₹900, cold plunge ₹600, HBOT ₹4,500, IV drip ₹3,500, red-light ₹800,
DEXA ₹3,500, VO2/CPET ₹6,000, blood panel ₹5,500, consult ₹1,500, strength coaching ₹1,800.

## Payment gateways (MDR modelled, GST 18% on fee)
| Gateway | Base MDR | Recurring add | Settlement | Mandate |
|---------|----------|---------------|------------|---------|
| Razorpay | 2.00% | +0.99% | T+2 | ✓ (Subscriptions) |
| Cashfree | 1.95% | — | T+1 | ✓ (UPI AutoPay / e-mandate) |
| PayU | 2.00% | — | T+2 | ✓ |
| UPI AutoPay | 0.00% | — | T+1 | ✓ (preferred for subscriptions — nil MDR) |
| Card (POS) | 2.00% | — | T+2 | ✗ |
| Cash | 0.00% | — | instant | ✗ |

`billing.gateway_fee(amount, gateway, recurring)` → `{rate, fee, net}`; `summary()` reconciles gross/fees/net
by gateway and computes **MRR** from active subscriptions. Recurring charges prefer UPI AutoPay (nil MDR) in the
simulation; mixed gateways are used so reconciliation is exercised.

## Sources
- [Longevity Inc. — Open Magazine](https://openthemagazine.com/india/longevity-inc-india-joins-the-immortality-race)
- [The 'Longevity Clinic' Boom — purshoLOGY](https://www.purshology.com/2026/05/the-longevity-clinic-boom-why-india-is-5-years-behind-the-us-health-market/)
- [Longevity clinic vs health check-up — Socialtalky](https://socialtalky.com/longevity-clinic-in-india/)
- [Razorpay vs PayU vs Cashfree — Analytics Insight](https://www.analyticsinsight.net/finance/razorpay-vs-payu-vs-cashfree-which-is-the-best-payment-gateway-for-2026)
- [Best payment gateways India — ParityDeals](https://www.paritydeals.com/blog/best-payment-gateways-india-2026/)
