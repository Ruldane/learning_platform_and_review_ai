import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { API } from "@/test/councilApi";
import { embeddingOut, onboardingApi } from "@/test/onboardingApi";
import { server } from "@/test/server";
import { useEmbeddingProgress } from "./useEmbeddingProgress";

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

describe("useEmbeddingProgress", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("embedding progress polls until present, then stops reading", async () => {
    const api = onboardingApi({
      settings: {},
      embedding: [embeddingOut(10), embeddingOut(42), embeddingOut(null, true)],
    });
    server.use(...api.handlers);
    const { result } = renderHook(() => useEmbeddingProgress(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.percent).toBe(10));

    await advance(3_100);
    await waitFor(() => expect(result.current.data?.percent).toBe(42));
    expect(api.reads.embedding).toBe(2);

    await advance(3_100);
    await waitFor(() => expect(result.current.data?.present).toBe(true));
    expect(result.current.data?.percent).toBe(100);

    const settled = api.reads.embedding;
    await advance(30_000);
    expect(api.reads.embedding).toBe(settled);
  });

  it("does not read again before 3 seconds have passed", async () => {
    const api = onboardingApi({ settings: {}, embedding: [embeddingOut(10)] });
    server.use(...api.handlers);
    renderHook(() => useEmbeddingProgress(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(api.reads.embedding).toBe(1));
    await advance(2_500);
    expect(api.reads.embedding).toBe(1);
    await advance(1_000);
    await waitFor(() => expect(api.reads.embedding).toBe(2));
  });

  it("keeps reading after a failed read", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/health/embedding`, () => {
        reads += 1;
        return reads === 1 ? HttpResponse.error() : HttpResponse.json(embeddingOut(null, true));
      }),
    );
    const { result } = renderHook(() => useEmbeddingProgress(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    await advance(3_100);
    await waitFor(() => expect(result.current.data?.present).toBe(true));
  });
});
