import { useEffect, useState } from "react";

import { ApiError } from "../api/client";

export type ApiState<T> = {
  data: T | undefined;
  error: ApiError | undefined;
  /** True while a request is in flight; `data` still holds the last result. */
  loading: boolean;
};

/**
 * Run `load` whenever `key` changes, `delay` ms after the last change.
 * `key: null` means "nothing to load" (e.g. the form is invalid) and clears
 * the result. Superseded requests are aborted.
 */
export function useApi<T>(
  key: string | null,
  load: (signal: AbortSignal) => Promise<T>,
  delay = 0,
): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({
    data: undefined,
    error: undefined,
    loading: key !== null,
  });

  useEffect(() => {
    if (key === null) {
      setState({ data: undefined, error: undefined, loading: false });
      return;
    }
    setState((s) => ({ ...s, loading: true }));
    const controller = new AbortController();
    const timer = setTimeout(() => {
      load(controller.signal).then(
        (data) => setState({ data, error: undefined, loading: false }),
        (error: unknown) => {
          if (controller.signal.aborted) return;
          setState((s) => ({
            data: s.data,
            error:
              error instanceof ApiError
                ? error
                : new ApiError("Something went wrong.", "unknown"),
            loading: false,
          }));
        },
      );
    }, delay);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // `load` is recreated every render; `key` captures everything it depends on.
  }, [key, delay]);

  return state;
}
