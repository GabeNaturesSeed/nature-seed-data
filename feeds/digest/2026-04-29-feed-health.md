# Feed Health — 2026-04-29

## Summary

| Channel | Coverage | Drift | Quality Issues |
|---|---|---|---|
| walmart | ERROR | ERROR | Expecting value: line 1 column 1 (char 0) |
| amazon | ERROR | ERROR | 400 Client Error:  for url: https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items?sellerId=&includedData=summaries%2Cattributes%2Coffers |
| google_merchant | ERROR | ERROR | 400 Client Error: Bad Request for url: https://oauth2.googleapis.com/token |
| klaviyo | ERROR | ERROR | 400 Client Error: Bad Request for url: https://a.klaviyo.com/api/catalog-items?page%5Bsize%5D=100 |
| shopper_approved | ERROR | ERROR | 404 Client Error: Not Found for url: https://api.shopperapproved.com/products/33157?token=17d6fb4162&limit=500 |
| reddit | ERROR | ERROR | Reddit catalog not found at docs/reddit-catalog/reddit_catalog.csv. Run the reddit-ads agent first. |
| facebook | ERROR | ERROR | not connected — Facebook Catalog API not yet configured |
| pinterest | ERROR | ERROR | not connected — Pinterest Catalog API not yet configured |

## Action Items

- [ ] **walmart**: investigate error — Expecting value: line 1 column 1 (char 0)
- [ ] **amazon**: investigate error — 400 Client Error:  for url: https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items?sellerId=&includedData=summaries%2Cattributes%2Coffers
- [ ] **google_merchant**: investigate error — 400 Client Error: Bad Request for url: https://oauth2.googleapis.com/token
- [ ] **klaviyo**: investigate error — 400 Client Error: Bad Request for url: https://a.klaviyo.com/api/catalog-items?page%5Bsize%5D=100
- [ ] **shopper_approved**: investigate error — 404 Client Error: Not Found for url: https://api.shopperapproved.com/products/33157?token=17d6fb4162&limit=500
- [ ] **reddit**: investigate error — Reddit catalog not found at docs/reddit-catalog/reddit_catalog.csv. Run the reddit-ads agent first.
- [ ] **facebook**: investigate error — not connected — Facebook Catalog API not yet configured
- [ ] **pinterest**: investigate error — not connected — Pinterest Catalog API not yet configured
