import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API, goalOut, proposalOut, sessionOut } from "@/test/councilApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useChooseProposal } from "./useChooseProposal";

const apiError = (code: string, details: unknown = null) => ({
  error: { code, message: "Message du serveur.", details },
});

function setup() {
  const reads = { goal: 0, proposals: 0, session: 0 };
  server.use(
    http.get(`${API}/goals/g1`, () => {
      reads.goal += 1;
      return HttpResponse.json(goalOut());
    }),
    http.get(`${API}/goals/g1/proposals`, () => {
      reads.proposals += 1;
      return HttpResponse.json([proposalOut("p1", 1)]);
    }),
    http.get(`${API}/sessions/c1`, () => {
      reads.session += 1;
      return HttpResponse.json(sessionOut("c1", "completed", { last_seq: 50 }));
    }),
  );
  const hook = renderHook(() => useChooseProposal("g1", "c1"), { wrapper: createQueryWrapper() });
  return { hook, reads };
}

afterEach(() => useSessionStore.getState().reset("c1"));

describe("useChooseProposal", () => {
  it("posts the choice (and the mix) then reads the state again", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/proposals/p1/choose`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(
          { council_session_id: "c1", status: "running", already_chosen: false },
          { status: 202 },
        );
      }),
    );
    const { hook, reads } = setup();
    await act(() => hook.result.current.choose("p1", "p2"));
    expect(bodies).toEqual([{ mix_with: "p2" }]);
    expect(hook.result.current.notice).toBeNull();
    expect(hook.result.current.error).toBeNull();
    expect(reads.session).toBe(1);
  });

  it("turns proposal_outdated and council_not_waiting into notices, and reads again", async () => {
    server.use(
      http.post(`${API}/proposals/p1/choose`, () =>
        HttpResponse.json(apiError("proposal_outdated"), { status: 409 }),
      ),
      http.post(`${API}/proposals/p2/choose`, () =>
        HttpResponse.json(apiError("council_not_waiting", { status: "completed" }), {
          status: 409,
        }),
      ),
    );
    const { hook } = setup();
    await act(() => hook.result.current.choose("p1"));
    expect(hook.result.current.notice).toMatch(/plus d'actualité/);
    expect(hook.result.current.error).toBeNull();
    await act(() => hook.result.current.choose("p2"));
    expect(hook.result.current.notice).toMatch(/état : Terminée/);
    expect(hook.result.current.error).toBeNull();
    // Le statut relu est appliqué au flux.
    await waitFor(() =>
      expect(useSessionStore.getState().sessions["c1"]?.status).toBe("completed"),
    );
  });

  it("reports already_chosen as a notice about the start date", async () => {
    server.use(
      http.post(`${API}/proposals/p1/choose`, () =>
        HttpResponse.json(
          { council_session_id: "c1", status: "running", already_chosen: true },
          { status: 202 },
        ),
      ),
    );
    const { hook } = setup();
    await act(() => hook.result.current.choose("p1"));
    expect(hook.result.current.notice).toMatch(/date de début est restée la même/);
  });

  it("keeps any other failure as an error", async () => {
    server.use(
      http.post(`${API}/proposals/p1/choose`, () =>
        HttpResponse.json(apiError("invalid_mix"), { status: 422 }),
      ),
    );
    const { hook, reads } = setup();
    await act(() => hook.result.current.choose("p1"));
    expect(hook.result.current.error).toBe("Message du serveur.");
    expect(hook.result.current.notice).toBeNull();
    expect(reads.session).toBe(0);
  });
});
