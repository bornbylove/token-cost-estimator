# Updating prices

All model prices live in [`src/tokencost/data/pricing.yaml`](../src/tokencost/data/pricing.yaml).
The app validates the file at startup and refuses to boot if it is invalid, and
CI runs the same validation on every push.

## Official sources

Only use the provider's own pricing page. Third-party comparison sites are
often out of date or disagree with each other.

| Provider  | Pricing page                                              |
| --------- | --------------------------------------------------------- |
| Anthropic | https://platform.claude.com/docs/en/about-claude/pricing  |
| OpenAI    | https://platform.openai.com/docs/pricing                  |
| Google    | https://ai.google.dev/gemini-api/docs/pricing             |

## What to record

Record the **standard, pay-as-you-go text price** in USD per million tokens.
Leave out batch, flex, cached input, fast/priority, and regional or data-residency
uplifts. Those are separate pricing dimensions, not the base price.

```yaml
- id: gpt-6-astra                 # the provider's API model id
  provider: OpenAI
  name: GPT-6 Astra               # display name
  input_price_per_million: "10.00"   # always a quoted string
  output_price_per_million: "50.00"
  long_context:                   # optional: only if the price depends on prompt size
    above_input_tokens: 272000    # tier applies when input tokens are strictly greater
    input_price_per_million: "20.00"
    output_price_per_million: "75.00"
  pricing_status: verified        # verified | illustrative
  effective_date: 2026-10-22      # the day you checked the source page
  valid_until: 2026-11-30         # optional: last day of an announced price
  source_url: https://platform.openai.com/docs/pricing
  notes: >-                       # optional: shown to users with every estimate
    Anything a user should know, e.g. an upcoming price change.
```

## Routine check (at least monthly)

1. Open each source page and compare each model's prices with the file.
2. If a price changed, update it. Either way, set `effective_date` to today.
   Estimates are flagged `stale` once `effective_date` is more than 90 days old
   (`TOKENCOST_STALE_AFTER_DAYS`).
3. Run `make check`, then commit with a message like
   `pricing: verify all models (2026-11-20)`.

## Announced price changes

When a provider announces a future price:

1. Set `valid_until` to the **last day** of the current price, and describe the
   change in `notes`.
2. On or after the change date, replace the prices, remove `valid_until`, and
   update `notes` and `effective_date`.

After `valid_until` passes, estimates are flagged `stale` until someone updates
the entry.

> Pending: `gemini-4-argon` changes to $4.00 / $20.00 on **2026-12-01**.

## Adding or retiring a model

- **Add:** use the provider's exact API model id as `id`; it must be lowercase
  letters, digits, `.` and `-`. Keep entries grouped by provider.
- **Retire:** delete the entry once the provider stops serving the model.
  Clients that still send the id get a `model_not_found` error.

## Tiers that aren't modelled yet

Tiers where the price depends on prompt size use `long_context`. For other
kinds of tiers, record the default tier, explain the others in `notes`, and
open an issue.
