import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

type Schemas = components["schemas"];
export type ModelInfo = Schemas["ModelInfo"];
export type Estimate = Schemas["Estimate"];
export type Comparison = Schemas["Comparison"];
export type TokenCountResult = Schemas["TokenCountResult"];
export type EstimateRequest = Schemas["EstimateRequest"];
export type CompareRequest = Schemas["CompareRequest"];

// Same origin in production (FastAPI serves the app) and in development (Vite
// proxies /api). Resolve fetch per call so tests can stub it.
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? "",
  fetch: (request) => globalThis.fetch(request),
});

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
  }
}

type Result<T> = { data?: T; error?: unknown; response: Response };

/** The data, or an ApiError carrying the API's error envelope message. */
export async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>;
  try {
    result = await request;
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError("Can't reach the server. Check your connection.", "network");
  }
  if (result.data !== undefined) return result.data;

  const envelope = result.error as { error?: { code?: string; message?: string } };
  throw new ApiError(
    envelope?.error?.message ?? `Request failed (${result.response.status}).`,
    envelope?.error?.code ?? "http_error",
  );
}
