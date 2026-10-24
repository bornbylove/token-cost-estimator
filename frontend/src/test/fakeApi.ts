import { vi } from "vitest";

import type { Comparison, Estimate, ModelInfo } from "../api/client";

export const MODELS: ModelInfo[] = [
  {
    id: "cheap-model",
    provider: "Acme",
    name: "Cheap model",
    input_price_per_million: "0.10",
    output_price_per_million: "0.50",
    long_context: {
      above_input_tokens: 100000,
      input_price_per_million: "0.50",
      output_price_per_million: "2.50",
    },
    pricing_status: "verified",
    effective_date: "2026-10-22",
    valid_until: null,
    source_url: "https://example.com/pricing",
    notes: null,
    stale: false,
  },
  {
    id: "big-model",
    provider: "Globex",
    name: "Big model",
    input_price_per_million: "10.00",
    output_price_per_million: "50.00",
    long_context: null,
    pricing_status: "verified",
    effective_date: "2026-01-01",
    valid_until: "2026-11-30",
    source_url: "https://example.org/pricing",
    notes: "Price rises on 2026-12-01.",
    stale: true,
  },
];

export function estimateFor(model: ModelInfo, body: Record<string, unknown>): Estimate {
  const perDay = body.requests_per_day as number | null;
  const total = model.id === "cheap-model" ? "0.000700" : "0.070000";
  return {
    model_id: model.id,
    provider: model.provider,
    model_name: model.name,
    input_tokens: body.input_tokens as number,
    output_tokens: body.output_tokens as number,
    price_tier: (body.input_tokens as number) > 100000 ? "long_context" : "standard",
    input_cost_usd: model.id === "cheap-model" ? "0.000300" : "0.030000",
    output_cost_usd: model.id === "cheap-model" ? "0.000400" : "0.040000",
    total_cost_usd: total,
    currency: "USD",
    projection: perDay
      ? {
          requests_per_day: perDay,
          days_per_month: 30,
          daily_cost_usd: model.id === "cheap-model" ? "3.500000" : "350.000000",
          monthly_cost_usd: model.id === "cheap-model" ? "105.000000" : "10500.000000",
        }
      : null,
    pricing_status: model.pricing_status,
    effective_date: model.effective_date,
    valid_until: model.valid_until ?? null,
    stale: model.stale,
    notes: model.notes ?? null,
  };
}

type Handler = (body: Record<string, unknown>) => { status?: number; json: unknown };

/** Stub fetch with handlers keyed by "METHOD /path". Returns the spy. */
export function fakeApi(overrides: Record<string, Handler> = {}) {
  const handlers: Record<string, Handler> = {
    "GET /api/v1/models": () => ({ json: MODELS }),
    "POST /api/v1/estimate": (body) => {
      const model = MODELS.find((m) => m.id === body.model_id);
      return model
        ? { json: estimateFor(model, body) }
        : { status: 404, json: { error: { code: "model_not_found", message: "Unknown model" } } };
    },
    "POST /api/v1/compare": (body) => {
      const ids = (body.model_ids as string[] | null) ?? MODELS.map((m) => m.id);
      const estimates = MODELS.filter((m) => ids.includes(m.id)).map((m) =>
        estimateFor(m, body),
      );
      const comparison: Comparison = {
        estimates,
        cheapest_model_ids: [estimates[0]!.model_id],
      };
      return { json: comparison };
    },
    "POST /api/v1/tokens/count": () => ({
      json: {
        characters: 11,
        tokens: 1234,
        method: "approximate",
        tokenizer: "o200k_base",
        note: "Approximate.",
      },
    }),
    ...overrides,
  };

  const spy = vi.fn(async (request: Request) => {
    const key = `${request.method} ${new URL(request.url).pathname}`;
    const handler = handlers[key];
    if (!handler) throw new Error(`No fake for ${key}`);
    // Read a clone so bodiesFor() can still read the original.
    const body = request.method === "POST" ? await request.clone().json() : {};
    const { status = 200, json } = handler(body);
    return new Response(JSON.stringify(json), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

/** Bodies of every call to `path`, in order. */
export async function bodiesFor(spy: ReturnType<typeof fakeApi>, path: string) {
  const requests = spy.mock.calls
    .map(([request]) => request)
    .filter((r) => new URL(r.url).pathname === path);
  return Promise.all(requests.map((r) => r.clone().json()));
}
