# Seasonal Reorder Flow — Manual UI Setup

Flow ID: `Vzp5Nb`
Klaviyo UI: https://www.klaviyo.com/flow/Vzp5Nb/edit

## Templates Uploaded

| Email | Template ID | Subject Line |
|---|---|---|
| Email 1 — Replant Moment | Ttbinc | Time to reseed your {{ person\|lookup:'last_category_purchased'\|default:'lawn' }}? |
| Email 2 — Planting Guide | R3Jnf6 | How to prep your soil this spring |
| Email 3 — Social Proof | Sd9d8W | What 1,200+ customers planted this April |
| Email 4 — Urgency | UxWSUE | Spring planting window is closing — order now |

## Steps to Complete in Klaviyo UI

1. Open https://www.klaviyo.com/flow/Vzp5Nb/edit
2. Verify trigger: **Segment trigger → WdpJti (Warm)**. If missing, add it.
3. For **Email 1** (send immediately on trigger):
   - Click the first email block → "Edit" → "Change template" → paste template ID
   - Set subject line from table above
   - Set sender: `customercare@naturesseed.com` | `Nature's Seed`
4. Add **Time Delay** of **7 days** after Email 1
5. For **Email 2** (Day 7): assign template, set subject
6. Add **Time Delay** of **3 days** (total Day 10)
7. For **Email 3** (Day 10): assign template, set subject
8. Add **Time Delay** of **6 days** (total Day 16)
9. For **Email 4** (Day 16): assign template, set subject
10. Add suppression filter to each email: exclude anyone who placed an order in last 48h
11. Enable Smart Send Time on each email
12. Click **Activate Flow**

## Suppression Rules (per suppression-rules.md)

- Exclude: Winback flow recipients, NOT-E90 (VirYfN), Unsubscribed 730+ days

## Verification After Activation

- Check flow analytics after 24h: confirm "Messages Sent" counter is incrementing
- New Warm RFM entries will enter this flow immediately after activation
