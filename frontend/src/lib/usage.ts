import { useSearchParams } from "react-router";

import { parseCount } from "./format";

// Mirrors the API's limits (src/tokencost/core/schemas.py).
export const MAX_TOKENS = 1_000_000_000_000;
export const MAX_REQUESTS_PER_DAY = 10_000_000;

/** Raw form text, kept in the URL so every result is a shareable link. */
export type UsageFields = { input: string; output: string; perDay: string };

export type Usage = {
  input_tokens: number;
  output_tokens: number;
  requests_per_day: number | null;
};

export type UsageErrors = Partial<Record<keyof UsageFields, string>>;

export const DEFAULT_FIELDS: UsageFields = { input: "3k", output: "800", perDay: "" };

export function validateUsage(fields: UsageFields): {
  usage: Usage | null;
  errors: UsageErrors;
} {
  const errors: UsageErrors = {};
  const count = (field: keyof UsageFields, max: number, min = 0) => {
    const value = parseCount(fields[field]);
    if (value === null) errors[field] = "Enter a whole number, like 3000 or 3k.";
    else if (value < min || value > max)
      errors[field] = `Must be between ${min} and ${max.toLocaleString("en-US")}.`;
    return value ?? 0;
  };

  const input_tokens = count("input", MAX_TOKENS);
  const output_tokens = count("output", MAX_TOKENS);
  const requests_per_day =
    fields.perDay.trim() === "" ? null : count("perDay", MAX_REQUESTS_PER_DAY, 1);

  const valid = Object.keys(errors).length === 0;
  return {
    usage: valid ? { input_tokens, output_tokens, requests_per_day } : null,
    errors,
  };
}

const PARAM: Record<keyof UsageFields, string> = {
  input: "in",
  output: "out",
  perDay: "day",
};

/** URL query state: usage fields (?in=3k&out=800&day=5000) plus page extras. */
export function useQueryState() {
  const [params, setParams] = useSearchParams();

  const fields: UsageFields = {
    input: params.get(PARAM.input) ?? DEFAULT_FIELDS.input,
    output: params.get(PARAM.output) ?? DEFAULT_FIELDS.output,
    perDay: params.get(PARAM.perDay) ?? DEFAULT_FIELDS.perDay,
  };

  const set = (name: string, value: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value === "") next.delete(name);
        else next.set(name, value);
        return next;
      },
      { replace: true },
    );

  return {
    fields,
    setField: (field: keyof UsageFields, value: string) => set(PARAM[field], value),
    get: (name: string) => params.get(name),
    set,
  };
}

/** Query string carrying the same usage to another page. */
export function usageQuery(fields: UsageFields, extra: Record<string, string> = {}) {
  const params = new URLSearchParams();
  params.set(PARAM.input, fields.input);
  params.set(PARAM.output, fields.output);
  if (fields.perDay) params.set(PARAM.perDay, fields.perDay);
  for (const [name, value] of Object.entries(extra)) params.set(name, value);
  return params.toString();
}
