import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { MarketFilters } from "./types";

export async function readMarket(filters: MarketFilters, signal: AbortSignal) {
  return unwrap(await api.GET("/skill-market", { params: { query: filters }, signal }));
}
