import { useId, useState } from "react";

import { api, ApiError, type TokenCountResult, unwrap } from "../api/client";
import { formatInt } from "../lib/format";
import type { UsageErrors, UsageFields } from "../lib/usage";

type Props = {
  fields: UsageFields;
  errors: UsageErrors;
  onChange: (field: keyof UsageFields, value: string) => void;
};

export function UsageForm({ fields, errors, onChange }: Props) {
  return (
    <div className="usage-form">
      <CountField
        label="Input tokens"
        hint="Prompt size of one request"
        value={fields.input}
        error={errors.input}
        onChange={(v) => onChange("input", v)}
      />
      <CountField
        label="Output tokens"
        hint="Response size of one request"
        value={fields.output}
        error={errors.output}
        onChange={(v) => onChange("output", v)}
      />
      <CountField
        label="Requests per day"
        hint="Optional, for daily and monthly totals"
        placeholder="e.g. 5k"
        value={fields.perDay}
        error={errors.perDay}
        onChange={(v) => onChange("perDay", v)}
      />
      <TokenCounter onUse={(tokens) => onChange("input", String(tokens))} />
    </div>
  );
}

type FieldProps = {
  label: string;
  hint: string;
  value: string;
  error: string | undefined;
  placeholder?: string;
  onChange: (value: string) => void;
};

function CountField({ label, hint, value, error, placeholder, onChange }: FieldProps) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        inputMode="decimal"
        autoComplete="off"
        spellCheck={false}
        value={value}
        placeholder={placeholder}
        aria-invalid={error !== undefined}
        aria-describedby={`${id}-hint`}
        onChange={(e) => onChange(e.target.value)}
      />
      <span id={`${id}-hint`} className={error ? "field-error" : "field-hint"}>
        {error ?? hint}
      </span>
    </div>
  );
}

/** Paste text, count its tokens on the server, and use that as input tokens. */
function TokenCounter({ onUse }: { onUse: (tokens: number) => void }) {
  const id = useId();
  const [text, setText] = useState("");
  const [result, setResult] = useState<TokenCountResult>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  async function count() {
    setBusy(true);
    setError(undefined);
    try {
      const counted = await unwrap(
        api.POST("/api/v1/tokens/count", { body: { text } }),
      );
      setResult(counted);
      onUse(counted.tokens);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't count tokens.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="token-counter">
      <summary>Don't know your token count? Paste your prompt</summary>
      <label htmlFor={id} className="visually-hidden">
        Prompt text
      </label>
      <textarea
        id={id}
        rows={5}
        value={text}
        placeholder="Paste a typical prompt…"
        onChange={(e) => setText(e.target.value)}
      />
      <div className="token-counter-actions">
        <button type="button" onClick={count} disabled={busy || text === ""}>
          {busy ? "Counting…" : "Count and use as input tokens"}
        </button>
        <span role="status" className="field-hint">
          {error ??
            (result &&
              `≈ ${formatInt(result.tokens)} tokens. Approximate: each model counts a bit differently.`)}
        </span>
      </div>
    </details>
  );
}
