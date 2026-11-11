import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { API, memoryBackend, readHandlers, statsOut } from "../fixtures";
import { isReindexActive, useMemoryStats, useReindex } from "./useMemoryStats";

type Status = "idle" | "queued" | "running" | "done" | "failed";
const at = (status: Status) => ({ reindex: { status, done: 0, total: 0, error: null } });

describe("useMemoryStats", () => {
  it("keeps the six kinds even when the API sends fewer", async () => {
    server.use(...readHandlers(memoryBackend({ stats: statsOut({ by_kind: { acquis: 2 } }) })));
    const { result } = renderHook(() => useMemoryStats(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.by_kind.acquis).toBe(2));
    expect(result.current.data?.by_kind.offre).toBe(0);
  });

  it("polls only while the reindex is queued or running", () => {
    expect(isReindexActive(at("queued"))).toBe(true);
    expect(isReindexActive(at("running"))).toBe(true);
    expect(isReindexActive(at("done"))).toBe(false);
    expect(isReindexActive(at("failed"))).toBe(false);
    expect(isReindexActive(undefined)).toBe(false);
  });

  it("asks for a reindex and reads the stats again", async () => {
    const backend = memoryBackend();
    let asked = 0;
    server.use(
      ...readHandlers(backend),
      http.post(`${API}/memory/reindex`, () => {
        asked += 1;
        backend.stats = statsOut({ reindex: { status: "queued", done: 0, total: 5, error: null } });
        return HttpResponse.json(backend.stats.reindex, { status: 202 });
      }),
    );
    const { result } = renderHook(() => ({ stats: useMemoryStats(), reindex: useReindex() }), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.stats.isSuccess).toBe(true));
    result.current.reindex.mutate();
    await waitFor(() => expect(result.current.stats.data?.reindex.status).toBe("queued"));
    expect(asked).toBe(1);
  });
});
