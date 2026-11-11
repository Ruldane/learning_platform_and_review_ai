import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { API, apiError, itemOut, memoryBackend, readHandlers } from "../fixtures";
import { useItemMutations } from "./useItemMutations";
import { useMemoryStats } from "./useMemoryStats";

interface Sent {
  method: string;
  path: string;
  body: unknown;
}

function setup() {
  const backend = memoryBackend();
  const sent: Sent[] = [];
  const record = async (request: Request) => {
    const text = await request.text();
    const path = new URL(request.url).pathname.replace("/api/v1", "");
    sent.push({ method: request.method, path, body: text ? JSON.parse(text) : null });
  };
  server.use(
    ...readHandlers(backend),
    http.patch(`${API}/memory/items/:id`, async ({ request }) => {
      await record(request);
      return HttpResponse.json(itemOut());
    }),
    http.delete(`${API}/memory/items/:id`, async ({ request }) => {
      await record(request);
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(`${API}/memory/items`, async ({ request }) => {
      await record(request);
      return HttpResponse.json(itemOut({ id: "n1" }), { status: 201 });
    }),
    http.post(`${API}/memory/items/:id/merge`, async ({ request }) => {
      await record(request);
      return HttpResponse.json(itemOut());
    }),
  );
  const hook = renderHook(() => ({ m: useItemMutations(), stats: useMemoryStats() }), {
    wrapper: createQueryWrapper(),
  });
  return { backend, sent, hook };
}

const statsCalls = (backend: ReturnType<typeof memoryBackend>) =>
  backend.requests.filter((r) => r.url.pathname.endsWith("/stats")).length;

describe("useItemMutations", () => {
  it("confirms a decision with PATCH status active, then invalidates the stats", async () => {
    const { backend, sent, hook } = setup();
    await waitFor(() => expect(hook.result.current.stats.isSuccess).toBe(true));
    const before = statsCalls(backend);
    hook.result.current.m.confirm.mutate("i9");
    await waitFor(() => expect(hook.result.current.m.confirm.isSuccess).toBe(true));
    expect(sent).toEqual([
      { method: "PATCH", path: "/memory/items/i9", body: { status: "active" } },
    ]);
    expect(statsCalls(backend)).toBeGreaterThan(before);
  });

  it("rejects a decision with DELETE and merges with other_ids", async () => {
    const { sent, hook } = setup();
    hook.result.current.m.reject.mutate("i9");
    await waitFor(() => expect(hook.result.current.m.reject.isSuccess).toBe(true));
    hook.result.current.m.merge.mutate({ id: "i1", otherIds: ["i3", "i4"] });
    await waitFor(() => expect(hook.result.current.m.merge.isSuccess).toBe(true));
    expect(sent).toEqual([
      { method: "DELETE", path: "/memory/items/i9", body: null },
      { method: "POST", path: "/memory/items/i1/merge", body: { other_ids: ["i3", "i4"] } },
    ]);
  });

  it("creates and edits an item", async () => {
    const { sent, hook } = setup();
    const value = { title: "T", text: "X", tags: [], level: "declare" as const };
    hook.result.current.m.create.mutate({ kind: "acquis", ...value });
    await waitFor(() => expect(hook.result.current.m.create.isSuccess).toBe(true));
    hook.result.current.m.update.mutate({ id: "i1", value });
    await waitFor(() => expect(hook.result.current.m.update.isSuccess).toBe(true));
    expect(sent.map((s) => s.method)).toEqual(["POST", "PATCH"]);
  });

  it("surfaces the readable merge refusal of the server", async () => {
    const { hook } = setup();
    server.use(
      http.post(`${API}/memory/items/:id/merge`, () =>
        apiError("merge_kind_mismatch", "Les éléments à fusionner doivent être du même type.", 409),
      ),
    );
    hook.result.current.m.merge.mutate({ id: "i1", otherIds: ["i2"] });
    await waitFor(() => expect(hook.result.current.m.merge.isError).toBe(true));
    expect(hook.result.current.m.merge.error?.message).toBe(
      "Les éléments à fusionner doivent être du même type.",
    );
  });
});
