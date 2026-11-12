import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, goalOut } from "@/test/councilApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useGoal } from "./useGoal";
import { useGoals } from "./useGoals";

describe("useGoals", () => {
  it("sorts the goals from the newest to the oldest", async () => {
    server.use(
      http.get(`${API}/goals`, () =>
        HttpResponse.json([
          goalOut({ id: "a", created_at: "2026-11-01T10:00:00Z" }),
          goalOut({ id: "b", created_at: "2026-11-09T10:00:00Z" }),
          goalOut({ id: "c", created_at: "2026-11-05T10:00:00Z" }),
        ]),
      ),
    );
    const { result } = renderHook(() => useGoals(), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.map((g) => g.id)).toEqual(["b", "c", "a"]));
  });
});

describe("useGoal", () => {
  it("reads one goal", async () => {
    server.use(http.get(`${API}/goals/g1`, () => HttpResponse.json(goalOut())));
    const { result } = renderHook(() => useGoal("g1"), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.id).toBe("g1"));
  });

  it("does not poll unless the program is awaited", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/goals/g1`, () => {
        reads += 1;
        return HttpResponse.json(goalOut());
      }),
    );
    const { result } = renderHook(() => useGoal("g1", false), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 2300));
    expect(reads).toBe(1);
  }, 8000);

  it("polls every 2 s while the program session is awaited, then stops", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/goals/g1`, () => {
        reads += 1;
        return HttpResponse.json(reads < 2 ? goalOut() : goalOut({ program_session_id: "pr1" }));
      }),
    );
    const { result } = renderHook(() => useGoal("g1", true), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data?.program_session_id).toBe("pr1"), {
      timeout: 5000,
    });
    const seen = reads;
    await new Promise((resolve) => setTimeout(resolve, 2300));
    expect(reads).toBe(seen);
  }, 12000);
});
