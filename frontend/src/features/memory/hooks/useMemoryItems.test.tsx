import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { NO_FILTERS } from "../components/viewFixtures";
import { memoryBackend, readHandlers } from "../fixtures";
import type { ItemsQuery } from "../types";
import { useMemoryItems } from "./useMemoryItems";

const query = (overrides: Partial<ItemsQuery> = {}): ItemsQuery => ({
  filters: NO_FILTERS,
  status: "active",
  offset: 0,
  limit: 25,
  ...overrides,
});

describe("useMemoryItems", () => {
  it("loads a page of rows without their text", async () => {
    server.use(...readHandlers(memoryBackend()));
    const { result } = renderHook(() => useMemoryItems(query()), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.total).toBe(2));
    expect(result.current.data?.items.map((i) => i.title)).toEqual([
      "Attention",
      "Backpropagation",
    ]);
    expect(result.current.data?.items[0]).not.toHaveProperty("text");
  });

  it("sends the filters, the status and the paging as query parameters", async () => {
    const backend = memoryBackend();
    server.use(...readHandlers(backend));
    const filters = { ...NO_FILTERS, kind: "lecon" as const, tag: " nlp ", author: "user" };
    const { result } = renderHook(
      () => useMemoryItems(query({ filters, status: "pending", offset: 50, limit: 10 })),
      { wrapper: createQueryWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const params = backend.requests[0]!.url.searchParams;
    expect(Object.fromEntries(params)).toEqual({
      kind: "lecon",
      tag: "nlp",
      author: "user",
      status: "pending",
      limit: "10",
      offset: "50",
    });
  });

  it("turns the day bounds into instants covering the whole days", async () => {
    const backend = memoryBackend();
    server.use(...readHandlers(backend));
    const filters = { ...NO_FILTERS, since: "2026-11-01", until: "2026-11-02" };
    const { result } = renderHook(() => useMemoryItems(query({ filters })), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const params = backend.requests[0]!.url.searchParams;
    expect(params.get("since")).toBe(new Date("2026-11-01T00:00:00").toISOString());
    expect(params.get("until")).toBe(new Date("2026-11-02T23:59:59.999").toISOString());
  });
});
