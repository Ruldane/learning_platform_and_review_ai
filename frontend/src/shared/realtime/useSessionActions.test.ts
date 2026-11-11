import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { fr } from "@/shared/i18n/fr";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { selectSession, useSessionStore } from "./sessionStore";
import { interrupt, snapshot, started } from "./testEvents";
import { useSessionActions, useStartSession } from "./useSessionActions";

const BASE = `${apiBaseUrl}/api/v1/sessions`;
const view = (status: string) => ({
  id: "s1",
  graph: "demo",
  status,
  last_seq: 1,
  pending_interrupt: null,
  error: null,
  cost_usd: 0,
  tokens_in: 0,
  tokens_out: 0,
  created_at: "2026-11-11T10:00:00Z",
  updated_at: "2026-11-11T10:00:00Z",
});
const apiError = (code: string, status: number, message = "Message du serveur") =>
  HttpResponse.json({ error: { code, message, details: null } }, { status });
const state = () => selectSession("s1")(useSessionStore.getState());

function renderActions() {
  return renderHook(() => useSessionActions("s1"), { wrapper: createQueryWrapper() });
}

describe("useSessionActions", () => {
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("resume posts the interrupt id and marks it answered", async () => {
    useSessionStore.getState().ingest("s1", [interrupt(1, "i1")]);
    let body: unknown = null;
    server.use(
      http.post(`${BASE}/s1/resume`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(view("running"), { status: 202 });
      }),
    );
    const { result } = renderActions();
    let ok = false;
    await act(async () => {
      ok = await result.current.resume("i1", { choice: "a" });
    });
    expect(ok).toBe(true);
    expect(body).toEqual({ interrupt_id: "i1", value: { choice: "a" } });
    expect(state().pendingInterrupt).toBeNull();
    expect(state().status).toBe("running");
    expect(result.current.error).toBeNull();
  });

  it("leaves a newer question alone when the answer arrives late", async () => {
    useSessionStore.getState().ingest("s1", [interrupt(1, "i1")]);
    server.use(
      http.post(`${BASE}/s1/resume`, () => {
        useSessionStore.getState().ingest("s1", [interrupt(2, "i2")]);
        return HttpResponse.json(view("running"), { status: 202 });
      }),
    );
    const { result } = renderActions();
    await act(() => result.current.resume("i1", "a"));
    expect(state().pendingInterrupt?.interrupt_id).toBe("i2");
    expect(state().status).toBe("waiting_user");
  });

  it("resume with a null id takes a paused session back to running", async () => {
    useSessionStore.getState().local("s1", { type: "snapshot", snapshot: snapshot("paused", 0) });
    server.use(
      http.post(`${BASE}/s1/resume`, () => HttpResponse.json(view("running"), { status: 202 })),
    );
    const { result } = renderActions();
    await act(() => result.current.resume(null, null));
    expect(state().status).toBe("running");
  });

  it("pause and cancel apply the status returned by the API", async () => {
    server.use(
      http.post(`${BASE}/s1/pause`, () => HttpResponse.json(view("paused"))),
      http.post(`${BASE}/s1/cancel`, () => HttpResponse.json(view("cancelled"))),
    );
    const { result } = renderActions();
    await act(() => result.current.pause());
    expect(state().status).toBe("paused");
    await act(() => result.current.cancel());
    expect(state().status).toBe("cancelled");
  });

  it("a paused response is not lifted by a late agent.started", async () => {
    useSessionStore.getState().ingest("s1", [started(1, "demo_critic")]);
    server.use(http.post(`${BASE}/s1/pause`, () => HttpResponse.json(view("paused"))));
    const { result } = renderActions();
    await act(() => result.current.pause());
    useSessionStore.getState().ingest("s1", [started(2, "demo_critic")]);
    expect(state().status).toBe("paused");
  });

  it("sends a message without ingesting the returned event", async () => {
    let body: unknown = null;
    server.use(
      http.post(`${BASE}/s1/message`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          {
            id: "e9",
            session_id: "s1",
            seq: 9,
            ts: "2026-11-11T10:00:00Z",
            agent: null,
            type: "user.message",
            payload: { text: "Bonjour" },
          },
          { status: 201 },
        );
      }),
    );
    const { result } = renderActions();
    await act(() => result.current.sendMessage("Bonjour"));
    expect(body).toEqual({ text: "Bonjour" });
    expect(state().lastSeq).toBe(0);
  });

  it("surfaces the French API error message", async () => {
    server.use(http.post(`${BASE}/s1/resume`, () => apiError("stale_interrupt", 409)));
    const { result } = renderActions();
    let ok = true;
    await act(async () => {
      ok = await result.current.resume("i1", "a");
    });
    expect(ok).toBe(false);
    await waitFor(() => expect(result.current.error).toBe(fr.session.errors.stale_interrupt));
  });

  it.each([
    ["pause", "session_not_pausable", 409],
    ["cancel", "session_not_cancellable", 409],
    ["message", "session_closed", 409],
    ["pause", "server_stopping", 503],
  ] as const)("maps %s → %s to its French message", async (route, code, status) => {
    server.use(http.post(`${BASE}/s1/${route}`, () => apiError(code, status)));
    const { result } = renderActions();
    await act(async () => {
      if (route === "message") await result.current.sendMessage("x");
      else await result.current[route]();
    });
    await waitFor(() => expect(result.current.error).toBe(fr.session.errors[code]));
  });

  it("falls back to the server message for an unknown code, and clears it on success", async () => {
    server.use(http.post(`${BASE}/s1/pause`, () => apiError("other_code", 400, "Autre souci.")));
    const { result } = renderActions();
    await act(() => result.current.pause());
    await waitFor(() => expect(result.current.error).toBe("Autre souci."));
    server.use(http.post(`${BASE}/s1/pause`, () => HttpResponse.json(view("paused"))));
    await act(() => result.current.pause());
    await waitFor(() => expect(result.current.error).toBeNull());
  });

  it("reports pending while a request is in flight", async () => {
    let release: () => void = () => undefined;
    server.use(
      http.post(`${BASE}/s1/pause`, async () => {
        await new Promise<void>((resolve) => (release = resolve));
        return HttpResponse.json(view("paused"));
      }),
    );
    const { result } = renderActions();
    let done: Promise<boolean> = Promise.resolve(true);
    act(() => {
      done = result.current.pause();
    });
    await waitFor(() => expect(result.current.pending).toBe(true));
    release();
    await act(() => done);
    await waitFor(() => expect(result.current.pending).toBe(false));
  });
});

describe("useStartSession", () => {
  it("posts the graph and input and returns the session id", async () => {
    let body: unknown = null;
    server.use(
      http.post(BASE, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ session_id: "s42" }, { status: 202 });
      }),
    );
    const { result } = renderHook(() => useStartSession(), { wrapper: createQueryWrapper() });
    let id = "";
    await act(async () => {
      id = await result.current("demo", { topic: "SQL" });
    });
    expect(id).toBe("s42");
    expect(body).toEqual({ graph: "demo", input: { topic: "SQL" } });
  });
});
