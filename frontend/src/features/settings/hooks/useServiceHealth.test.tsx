import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { healthReport, onboardingApi } from "@/test/onboardingApi";
import { server } from "@/test/server";
import { useServiceHealth } from "./useServiceHealth";

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

describe("useServiceHealth", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("reads the services every 5 seconds, and shows a service that comes back", async () => {
    const api = onboardingApi({
      settings: {},
      health: [
        healthReport({ qdrant: [false, "Qdrant ne répond pas."] }, "degraded"),
        healthReport({ qdrant: [true, "Disponible."] }),
      ],
    });
    server.use(...api.handlers);
    const { result } = renderHook(() => useServiceHealth(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.checks.qdrant?.ok).toBe(false));

    await advance(4_500);
    expect(api.reads.health).toBe(1);
    await advance(1_000);
    await waitFor(() => expect(result.current.data?.checks.qdrant?.ok).toBe(true));
    expect(api.reads.health).toBe(2);
  });
});
