import { useState } from "react";

import { formatUsd, formatUsdTick, niceTicks } from "../lib/format";

export type CostBar = {
  id: string;
  label: string;
  /** USD decimal string from the API. */
  value: string;
  highlighted: boolean;
};

type Props = {
  bars: CostBar[];
  /** What the values are, e.g. "Monthly cost". Used for screen readers. */
  measure: string;
};

/**
 * Horizontal bars, one per model, in the order given (cheapest first).
 * Emphasis form: the cheapest models in the accent hue and labeled, the rest
 * in the de-emphasis gray. Values live in the table beside it too.
 */
export function CostBars({ bars, measure }: Props) {
  const [active, setActive] = useState<string | null>(null);
  // Floats are fine for geometry; displayed values keep the exact strings.
  const max = Math.max(0, ...bars.map((b) => Number(b.value)));
  const ticks = niceTicks(max);
  const top = ticks[ticks.length - 1] ?? 0;

  if (top === 0) {
    return <p className="chart-empty">Every model costs $0.00 for this usage.</p>;
  }

  return (
    <figure className="cost-bars" aria-label={`${measure} by model`}>
      <div className="cost-bars-grid" role="list">
        {bars.map((bar) => {
          const pct = (Number(bar.value) / top) * 100;
          const isActive = active === bar.id;
          return (
            <div
              key={bar.id}
              role="listitem"
              tabIndex={0}
              className={`cost-bars-row${bar.highlighted ? " is-highlighted" : ""}${isActive ? " is-active" : ""}`}
              aria-label={`${bar.label}: ${formatUsd(bar.value)}${bar.highlighted ? ", cheapest" : ""}`}
              onPointerEnter={() => setActive(bar.id)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(bar.id)}
              onBlur={() => setActive(null)}
            >
              <span className="cost-bars-label">{bar.label}</span>
              <span className="cost-bars-track">
                {ticks.map((t) => (
                  <span
                    key={t}
                    className="cost-bars-gridline"
                    style={{ left: `${(t / top) * 100}%` }}
                  />
                ))}
                <span className="cost-bars-bar" style={{ width: `${pct}%` }} />
                {bar.highlighted && (
                  <span
                    className="cost-bars-value"
                    style={{ left: `min(${pct}%, calc(100% - 7rem))` }}
                  >
                    {formatUsd(bar.value)} · cheapest
                  </span>
                )}
                {isActive && (
                  <span
                    className="cost-bars-tooltip"
                    role="tooltip"
                    style={{ left: `min(${pct}%, calc(100% - 10rem))` }}
                  >
                    <strong>{formatUsd(bar.value)}</strong>
                    <span>{bar.label}</span>
                  </span>
                )}
              </span>
            </div>
          );
        })}
        <div className="cost-bars-axis" aria-hidden="true">
          <span />
          <span className="cost-bars-ticks">
            {ticks.map((t) => (
              <span key={t} style={{ left: `${(t / top) * 100}%` }}>
                {formatUsdTick(t)}
              </span>
            ))}
          </span>
        </div>
      </div>
    </figure>
  );
}
