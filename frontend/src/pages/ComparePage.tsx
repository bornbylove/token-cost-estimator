import { Link } from "react-router";

import { api, type Comparison, type ModelInfo, unwrap } from "../api/client";
import { CostBars } from "../components/CostBars";
import { CheckedDate, PriceNotices } from "../components/PriceMeta";
import { UsageForm } from "../components/UsageForm";
import { formatInt, formatUsd } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useQueryState, usageQuery, validateUsage } from "../lib/usage";
import { useModels } from "../lib/useModels";

export function ComparePage() {
  const query = useQueryState();
  const models = useModels();
  const { usage, errors } = validateUsage(query.fields);

  const all = models.data ?? [];
  const picked = (query.get("models") ?? "").split(",").filter(Boolean);
  // Ignore ids that no longer exist; none picked means all models.
  const selected = picked.filter((id) => all.some((m) => m.id === id));

  const request = usage && {
    ...usage,
    model_ids: selected.length > 0 ? selected : null,
  };
  const comparison = useApi(
    request && models.data ? JSON.stringify(request) : null,
    (signal) => unwrap(api.POST("/api/v1/compare", { body: request!, signal })),
    250,
  );

  const toggle = (id: string) => {
    const current = selected.length > 0 ? selected : all.map((m) => m.id);
    const next = current.includes(id)
      ? current.filter((x) => x !== id)
      : [...current, id];
    // All or none selected both mean "every model".
    query.set("models", next.length === all.length ? "" : next.join(","));
  };

  return (
    <>
      <header className="page-header">
        <h1>Compare models</h1>
        <p className="lede">
          The same usage on every model, cheapest first. Add requests per day to
          compare monthly cost.
        </p>
      </header>

      <section className="card filters" aria-label="Usage and models">
        <UsageForm fields={query.fields} errors={errors} onChange={query.setField} />
        {all.length > 0 && (
          <fieldset className="model-picker">
            <legend>Models</legend>
            {all.map((m) => (
              <label key={m.id} className="chip">
                <input
                  type="checkbox"
                  checked={selected.length === 0 || selected.includes(m.id)}
                  onChange={() => toggle(m.id)}
                />
                {m.name}
              </label>
            ))}
          </fieldset>
        )}
      </section>

      {(models.error ?? comparison.error) && (
        <p className="notice notice-error">
          {(models.error ?? comparison.error)!.message}
        </p>
      )}
      {comparison.data && (
        <div className={comparison.loading ? "is-loading" : undefined}>
          <ComparisonView comparison={comparison.data} models={all} />
        </div>
      )}
      <p className="result-footer">
        <Link to={`/?${usageQuery(query.fields)}`}>← Back to a single estimate</Link>
      </p>
    </>
  );
}

function ComparisonView({
  comparison,
  models,
}: {
  comparison: Comparison;
  models: ModelInfo[];
}) {
  const { estimates, cheapest_model_ids: cheapest } = comparison;
  const projected = estimates[0]?.projection != null;
  const measure = projected ? "Monthly cost" : "Cost per request";
  const first = estimates[0];
  const names = new Map(models.map((m) => [m.id, m.name]));

  return (
    <>
      <section className="card">
        <h2 className="card-title">{measure}</h2>
        {first && (
          <p className="card-subtitle">
            {formatInt(first.input_tokens)} input + {formatInt(first.output_tokens)}{" "}
            output tokens per request
            {first.projection &&
              `, ${formatInt(first.projection.requests_per_day)} requests/day`}
          </p>
        )}
        <CostBars
          measure={measure}
          bars={estimates.map((e) => ({
            id: e.model_id,
            label: names.get(e.model_id) ?? e.model_name,
            value: e.projection ? e.projection.monthly_cost_usd : e.total_cost_usd,
            highlighted: cheapest.includes(e.model_id),
          }))}
        />
      </section>

      <section className="card">
        <h2 className="card-title">Details</h2>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col">Provider</th>
                <th scope="col" className="num">
                  Per request
                </th>
                {projected && (
                  <>
                    <th scope="col" className="num">
                      Per day
                    </th>
                    <th scope="col" className="num">
                      Per month
                    </th>
                  </>
                )}
                <th scope="col">Prices checked</th>
              </tr>
            </thead>
            <tbody>
              {estimates.map((e) => (
                <tr key={e.model_id}>
                  <th scope="row">
                    {e.model_name}
                    {cheapest.includes(e.model_id) && (
                      <span className="badge badge-accent">Cheapest</span>
                    )}
                    {e.price_tier === "long_context" && (
                      <span className="badge">Long-prompt price</span>
                    )}
                  </th>
                  <td>{e.provider}</td>
                  <td className="num">{formatUsd(e.total_cost_usd)}</td>
                  {e.projection && (
                    <>
                      <td className="num">{formatUsd(e.projection.daily_cost_usd)}</td>
                      <td className="num">{formatUsd(e.projection.monthly_cost_usd)}</td>
                    </>
                  )}
                  <td>
                    <CheckedDate item={{ ...e, id: e.model_id }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <PriceNotices
          items={estimates.map((e) => ({ ...e, id: e.model_id, name: e.model_name }))}
        />
      </section>
    </>
  );
}
