import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, boardOut, proposalOut } from "@/test/councilApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useBoards } from "./useBoards";
import { useProposals } from "./useProposals";

describe("useProposals", () => {
  it("maps the proposals to view types", async () => {
    server.use(
      http.get(`${API}/goals/g1/proposals`, () =>
        HttpResponse.json([proposalOut("p1", 1, { duration_weeks: 12, weekly_hours: 7.5 })]),
      ),
    );
    const { result } = renderHook(() => useProposals("g1", null), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() =>
      expect(result.current.data?.[0]).toMatchObject({
        id: "p1",
        durationWeeks: 12,
        weeklyHours: 7.5,
        boardId: null,
        chosen: false,
      }),
    );
  });

  it("reloads when a new proposal.ready arrives, and only then", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/goals/g1/proposals`, () => {
        reads += 1;
        return HttpResponse.json([proposalOut(`p${reads}`, 1)]);
      }),
    );
    const { result, rerender } = renderHook(({ key }) => useProposals("g1", key), {
      wrapper: createQueryWrapper(),
      initialProps: { key: null as string | null },
    });
    await waitFor(() => expect(result.current.data?.[0]?.id).toBe("p1"));
    rerender({ key: null });
    expect(reads).toBe(1);
    rerender({ key: "e12" });
    await waitFor(() => expect(result.current.data?.[0]?.id).toBe("p2"));
    rerender({ key: "e12" });
    expect(reads).toBe(2);
  });
});

describe("useBoards", () => {
  it("maps the saved states to view types", async () => {
    server.use(
      http.get(`${API}/goals/g1/boards`, () =>
        HttpResponse.json([
          boardOut("b1", { title: "" }),
          boardOut("b2", { author: "user", scene: { elements: [] } }),
        ]),
      ),
    );
    const { result } = renderHook(() => useBoards("g1"), { wrapper: createQueryWrapper() });
    await waitFor(() => expect(result.current.data).toHaveLength(2));
    expect(result.current.data?.[0]).toMatchObject({
      id: "b1",
      title: "Carte du domaine",
      scene: null,
    });
    expect(result.current.data?.[1]).toMatchObject({
      id: "b2",
      author: "user",
      scene: { elements: [] },
    });
  });
});
