import { CheckedDate, PriceNotices } from "../components/PriceMeta";
import { formatCompact, formatUsd } from "../lib/format";
import { useModels } from "../lib/useModels";

export function PricingPage() {
  const models = useModels();

  return (
    <>
      <header className="page-header">
        <h1>Prices</h1>
        <p className="lede">
          Standard API prices in USD per million tokens, checked by hand against
          each provider's official pricing page. Batch, cached and priority rates
          aren't included.
        </p>
      </header>

      <section className="card">
        {models.error && <p className="notice notice-error">{models.error.message}</p>}
        {models.data && (
          <>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Model</th>
                    <th scope="col">Provider</th>
                    <th scope="col" className="num">
                      Input
                    </th>
                    <th scope="col" className="num">
                      Output
                    </th>
                    <th scope="col">Long prompts</th>
                    <th scope="col">Checked</th>
                  </tr>
                </thead>
                <tbody>
                  {models.data.map((m) => (
                    <tr key={m.id}>
                      <th scope="row">
                        {m.name}
                        <code className="model-id">{m.id}</code>
                      </th>
                      <td>
                        {m.source_url ? (
                          <a href={m.source_url} target="_blank" rel="noopener noreferrer">
                            {m.provider}
                          </a>
                        ) : (
                          m.provider
                        )}
                      </td>
                      <td className="num">{formatUsd(m.input_price_per_million)}</td>
                      <td className="num">{formatUsd(m.output_price_per_million)}</td>
                      <td>
                        {m.long_context ? (
                          <>
                            {formatUsd(m.long_context.input_price_per_million)} /{" "}
                            {formatUsd(m.long_context.output_price_per_million)}
                            <span className="muted">
                              {" "}
                              over {formatCompact(m.long_context.above_input_tokens)} input
                            </span>
                          </>
                        ) : (
                          <span className="muted">Same price</span>
                        )}
                      </td>
                      <td>
                        <CheckedDate item={m} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <PriceNotices items={models.data} />
          </>
        )}
      </section>
    </>
  );
}
