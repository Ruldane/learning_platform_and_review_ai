import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, programApi, programOut, validationSession } from "@/test/programApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useReviseProgram } from "./useReviseProgram";
import { useValidateProgram } from "./useValidateProgram";

const run = <T,>(hook: () => T) => renderHook(hook, { wrapper: createQueryWrapper() });

const failure = (code: string, message: string, details: unknown = null) => ({
  error: { code, message, details },
});

describe("useValidateProgram", () => {
  it("validates, then reads the program and the session again", async () => {
    const { handlers } = programApi({ program: programOut({ status: "validated" }) });
    server.use(
      ...handlers,
      http.post(`${API}/programs/p1/validate`, () =>
        HttpResponse.json(
          { program_id: "p1", session_id: null, status: "validated" },
          { status: 202 },
        ),
      ),
    );
    const { result } = run(() => useValidateProgram("p1"));
    await act(async () => result.current.validate());
    expect(result.current.error).toBeNull();
    await waitFor(() => expect(result.current.validated).toBe(true));
  });

  it("says a 422 over budget as an error", async () => {
    server.use(
      http.post(`${API}/programs/p1/validate`, () =>
        HttpResponse.json(
          failure("week_over_budget", "Semaine 2 : 760 min prévues, 714 au plus."),
          { status: 422 },
        ),
      ),
    );
    const { result } = run(() => useValidateProgram("p1"));
    await act(async () => result.current.validate());
    expect(result.current.error).toBe("Semaine 2 : 760 min prévues, 714 au plus.");
    expect(result.current.validated).toBe(false);
  });

  it("turns 409 program_not_waiting into a notice, not an error", async () => {
    server.use(
      http.post(`${API}/programs/p1/validate`, () =>
        HttpResponse.json(failure("program_not_waiting", "x", { status: "paused" }), {
          status: 409,
        }),
      ),
    );
    const { result } = run(() => useValidateProgram("p1"));
    await act(async () => result.current.validate());
    expect(result.current.error).toBeNull();
    expect(result.current.notice).toBe(
      "Le programme n'attend pas de validation pour l'instant (session : En pause). L'état a été relu.",
    );
  });
});

describe("useReviseProgram", () => {
  it("resumes the validation question with a revise answer and the note", async () => {
    let body: unknown = null;
    server.use(
      http.post(`${API}/sessions/s1/resume`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(validationSession("running"));
      }),
    );
    const { result } = run(() => useReviseProgram("p1"));
    let sent = false;
    await act(async () => {
      sent = await result.current.revise({
        sessionId: "s1",
        interruptId: "i1",
        note: "Moins de vidéos.",
      });
    });
    expect(sent).toBe(true);
    expect(body).toEqual({
      interrupt_id: "i1",
      value: { action: "revise", note: "Moins de vidéos." },
    });
  });

  it("says a stale question as a notice", async () => {
    server.use(
      http.post(`${API}/sessions/s1/resume`, () =>
        HttpResponse.json(failure("stale_interrupt", "x"), { status: 409 }),
      ),
    );
    const { result } = run(() => useReviseProgram("p1"));
    await act(async () => {
      await result.current.revise({ sessionId: "s1", interruptId: "i1", note: "x" });
    });
    expect(result.current.notice).toBe(
      "Cette question a déjà reçu une réponse. L'état a été relu.",
    );
  });
});
