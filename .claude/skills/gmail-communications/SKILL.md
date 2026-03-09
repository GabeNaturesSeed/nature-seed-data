# Gmail — Nature's Seed Communications

> Invoke this skill when any agent needs to search, read, or draft emails for Nature's Seed operations.

## Connection

Gmail is connected via MCP server. Available tools:

| Tool | Purpose |
|------|---------|
| `gmail_get_profile` | Get authenticated user's profile |
| `gmail_search_messages` | Search emails (Gmail search syntax) |
| `gmail_read_message` | Read full email by message ID |
| `gmail_read_thread` | Read entire conversation thread |
| `gmail_create_draft` | Create email draft |
| `gmail_list_drafts` | List existing drafts |

## Key Email Addresses

| Address | Purpose |
|---------|---------|
| customercare@naturesseed.com | Main customer-facing email (Klaviyo sender) |

## Search Syntax Quick Reference

```
# Customer inquiries
from:customer@example.com
subject:order

# Recent unread
is:unread newer_than:7d

# With attachments
has:attachment from:supplier

# Order-related
subject:(order OR invoice OR shipping)

# Date range
after:2026/01/01 before:2026/03/01

# Combine
is:unread from:*@naturesseed.com has:attachment
```

## Integration Points

- **Klaviyo**: Marketing emails sent via customercare@naturesseed.com
- **WooCommerce**: Order notifications, shipping confirmations
- **Support tickets**: Tracked in Klaviyo via "Ticket Created" (T9tMHp) / "Ticket Closed" (SQJSm8) metrics

## Guidelines for Drafting

When drafting customer-facing emails, ALWAYS invoke the `natures-seed-brand` skill first for:
- Tone & voice guidelines
- Subject line patterns
- CTA best practices
- Brand color references
