import { useId } from "react";
import { Link } from "react-router";

import { api, type Estimate, type ModelInfo, unwrap } from "../api/client";
import { CheckedDate, PriceNotices } from "../components/PriceMeta";
import { UsageForm } from "../components/UsageForm";
import { formatCompact, formatInt, formatUsd } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useQueryState, usageQuery, validateUsage } from "../lib/usage";
import { useModels } from "../lib/useModels";

export function EstimatePage() {
  const query = useQueryState();
  const models = useModels();
  const selectId = useId();
  const { usage, errors } = validateUsage(query.fields);

  const modelList = models.data ?? [];
  const requested = query.get("model");
  const model =
    modelList.find((m) => m.id === requested) ?? modelList[0] ?? undefined;

  const request =
    usage && model ? { model_id: model.id, ...usage } : null;
  const estimate = useApi(
    request && JSON.stringify(request),
    (signal) =>
      unwrap(api.POST("/api/v1/estimate", { body: request!, signal })),
    250,
  );

  return (
    <>
      <header className="page-header">
        <h1>Estimate a request</h1>
        <p className="lede">
          Pick a model and the size of one request. Add requests per day to see
          what it costs each month.
        </p>
      </header>

      <div className="split">
        <section className="card" aria-labelledby={`${selectId}-heading`}>
          <h2 id={`${selectId}-heading`} className="card-title">
            Usage
          </h2>
          <div className="field">
            <label htmlFor={selectId}>Model</label>
            <select
              id={selectId}
              value={model?.id ?? ""}
              disabled={modelList.length === 0}
              onChange={(e) => query.set("model", e.target.value)}
            >
              {groupByProvider(modelList).map(([provider, items]) => (
                <optgroup key={provider} label={provider}>
                  {items.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <UsageForm fields={query.fields} errors={errors} onChange={query.setField} />
        </section>

        <section
          className={`card result${estimate.loading ? " is-loading" : ""}`}
          aria-live="polite"
          aria-busy={estimate.loading}
        >
          <h2 className="card-title">Cost</h2>
          {models.error && <p className="notice notice-error">{models.error.message}</p>}
          {estimate.error && (
            <p className="notice notice-error">{estimate.error.message}</p>
          )}
          {estimate.data && model ? (
            <EstimateResult estimate={estimate.data} model={model} />
          ) : usage === null ? (
            <p className="muted">Fix the highlighted fields to see a cost.</p>
          ) : (
            !estimate.error && !models.error && <p className="muted">Calculating…</p>
          )}
          <p className="result-footer">
            <Link to={`/compare?${usageQuery(query.fields)}`}>
              Compare every model for this usage →
            </Link>
          </p>
        </section>
      </div>
    </>
  );
}

function EstimateResult({ estimate, model }: { estimate: Estimate; model: ModelInfo }) {
  const p = estimate.projection;
  const longPrompt = estimate.price_tier === "long_context" && model.long_context;
  const prices = longPrompt ? model.long_context! : model;

  return (
    <>
      <p className="hero-label">{p ? "Per month" : "Per request"}</p>
      <p className="hero-value">
        {formatUsd(p ? p.monthly_cost_usd : estimate.total_cost_usd)}
      </p>
      {p && (
        <p className="hero-sub">
          {formatUsd(p.daily_cost_usd)} per day · {formatUsd(estimate.total_cost_usd)}{" "}
          per request · {formatInt(p.requests_per_day)} requests/day over{" "}
          {p.days_per_month} days
        </p>
      )}

      <table className="breakdown">
        <caption className="visually-hidden">Cost breakdown for one request</caption>
        <tbody>
          <tr>
            <th scope="row">Input</th>
            <td>
              {formatInt(estimate.input_tokens)} tokens
              <span className="rate">× {formatUsd(prices.input_price_per_million)}/M</span>
            </td>
            <td className="num">{formatUsd(estimate.input_cost_usd)}</td>
          </tr>
          <tr>
            <th scope="row">Output</th>
            <td>
              {formatInt(estimate.output_tokens)} tokens
              <span className="rate">× {formatUsd(prices.output_price_per_million)}/M</span>
            </td>
            <td className="num">{formatUsd(estimate.output_cost_usd)}</td>
          </tr>
          <tr className="breakdown-total">
            <th scope="row">Per request</th>
            <td />
            <td className="num">{formatUsd(estimate.total_cost_usd)}</td>
          </tr>
        </tbody>
      </table>

      {longPrompt && (
        <p className="notice">
          <span aria-hidden="true">ⓘ</span> Long-prompt pricing applies: this request
          has more than {formatCompact(model.long_context!.above_input_tokens)} input
          tokens.
        </p>
      )}
      <PriceNotices
        items={[{ ...estimate, id: estimate.model_id, name: estimate.model_name }]}
      />
      <p className="meta">
        {estimate.model_name} prices checked{" "}
        <CheckedDate item={{ ...estimate, id: estimate.model_id }} />
        {model.source_url && (
          <>
            {" · "}
            <a href={model.source_url} target="_blank" rel="noopener noreferrer">
              {estimate.provider} pricing
            </a>
          </>
        )}
      </p>
    </>
  );
}

function groupByProvider(models: ModelInfo[]): [string, ModelInfo[]][] {
  const groups = new Map<string, ModelInfo[]>();
  for (const m of models) groups.set(m.provider, [...(groups.get(m.provider) ?? []), m]);
  return [...groups];
}
