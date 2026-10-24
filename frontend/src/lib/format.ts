// Display rules shared with the CLI (src/tokencost/cli/format.py).

const SUFFIXES: Record<string, number> = { k: 1_000, m: 1_000_000 };

/** Parse 3000, 3,000, 3_000, 3k, 1.5M. Returns null for anything else. */
export function parseCount(value: string): number | null {
  let text = value.trim().replaceAll(",", "").replaceAll("_", "").toLowerCase();
  let multiplier = 1;
  const suffix = SUFFIXES[text.slice(-1)];
  if (suffix !== undefined) {
    multiplier = suffix;
    text = text.slice(0, -1);
  }
  if (!/^\d+(\.\d+)?$/.test(text)) return null;
  const number = Number(text) * multiplier;
  // Round away float noise like 1.1 * 1000 = 1100.0000000000002.
  const rounded = Math.round(number);
  if (Math.abs(number - rounded) > 1e-6 || !Number.isSafeInteger(rounded)) return null;
  return rounded;
}

/**
 * Format a USD decimal string from the API without float conversion:
 * "10500.000000" -> "$10,500.00", "0.000700" -> "$0.0007".
 */
export function formatUsd(amount: string): string {
  const [whole = "0", fraction = ""] = amount.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `$${grouped}.${fraction.replace(/0+$/, "").padEnd(2, "0")}`;
}

export function formatInt(value: number): string {
  return value.toLocaleString("en-US");
}

/** 100000 -> "100K", 1500000 -> "1.5M"; other values get separators. */
export function formatCompact(value: number): string {
  for (const [divisor, suffix] of [
    [1_000_000, "M"],
    [1_000, "K"],
  ] as const) {
    if (value >= divisor && (value * 10) % divisor === 0) {
      return `${value / divisor}${suffix}`;
    }
  }
  return formatInt(value);
}

/** Axis tick label: "$0", "$350", "$2.5K", "$1.2M". */
export function formatUsdTick(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumSignificantDigits: 3,
  }).format(value);
}

/** Round axis ticks from 0 to at least `max`: steps of 1, 2, or 5 x 10^n. */
export function niceTicks(max: number, target = 4): number[] {
  if (!(max > 0)) return [0];
  const rough = max / target;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step =
    [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? 10 * magnitude;
  const ticks: number[] = [];
  for (let i = 0; ; i++) {
    // Multiply instead of accumulating so 0.1 steps don't drift.
    const tick = Number((i * step).toPrecision(12));
    ticks.push(tick);
    if (tick >= max) break;
  }
  return ticks;
}

export function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}
