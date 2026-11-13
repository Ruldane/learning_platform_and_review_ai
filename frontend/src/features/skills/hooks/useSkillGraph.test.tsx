import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { skillsApi } from "@/test/skillsApi";
import { GRAPH_REFRESH_MS, useSkillGraph } from "./useSkillGraph";

describe("useSkillGraph", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("refetches the graph every 30 seconds", async () => {
    const skills = skillsApi();
    server.use(...skills.handlers);
    renderHook(() => useSkillGraph(), { wrapper: createQueryWrapper() });
    await vi.waitFor(() => expect(skills.reads.graph).toBe(1));
    await act(() => vi.advanceTimersByTimeAsync(GRAPH_REFRESH_MS));
    await vi.waitFor(() => expect(skills.reads.graph).toBe(2));
    await act(() => vi.advanceTimersByTimeAsync(GRAPH_REFRESH_MS));
    await vi.waitFor(() => expect(skills.reads.graph).toBe(3));
  });

  it("refetches the graph when the browser tab comes back", async () => {
    const skills = skillsApi();
    server.use(...skills.handlers);
    renderHook(() => useSkillGraph(), { wrapper: createQueryWrapper() });
    await vi.waitFor(() => expect(skills.reads.graph).toBe(1));
    await act(async () => {
      window.dispatchEvent(new Event("visibilitychange"));
    });
    await vi.waitFor(() => expect(skills.reads.graph).toBe(2));
  });
});
