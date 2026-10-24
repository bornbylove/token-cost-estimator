import { api, type ModelInfo, unwrap } from "../api/client";
import { useApi } from "./useApi";

export function useModels() {
  return useApi<ModelInfo[]>("models", (signal) =>
    unwrap(api.GET("/api/v1/models", { signal })),
  );
}
