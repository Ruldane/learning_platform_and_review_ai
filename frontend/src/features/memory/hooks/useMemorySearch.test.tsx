import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { API, searchOut } from "../fixtures";
import { useMemorySearch } from "./useMemorySearch";

function captureSearch() {
  const bodies: unknown[] = [];
  server.use(
    http.post(`${API}/memory/search`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(searchOut);
    }),
  );
  return bodies;
}

describe("useMemorySearch", () => {
  it("posts the query, the kinds and k=8 by default, and returns scored hits", async () => {
    const bodies = captureSearch();
    const { result } = renderHook(() => useMemorySearch(), { wrapper: createQueryWrapper() });
    act(() => result.current.mutate({ query: "attention", kinds: ["document"] }));
    await waitFor(() => expect(result.current.data?.hits[0]?.score).toBe(0.834));
    expect(bodies).toEqual([{ query: "attention", kinds: ["document"], k: 8 }]);
    expect(result.current.data?.agentText).toContain("CONTENU_NON_FIABLE");
  });

  it("sends no kinds filter when none is picked and passes k through", async () => {
    const bodies = captureSearch();
    const { result } = renderHook(() => useMemorySearch(), { wrapper: createQueryWrapper() });
    act(() => result.current.mutate({ query: "x", kinds: [], k: 3 }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(bodies).toEqual([{ query: "x", kinds: null, k: 3 }]);
  });
});
