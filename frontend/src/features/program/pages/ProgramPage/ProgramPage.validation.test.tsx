import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, programApi, programOut, validationSession } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ProgramPage } from "./ProgramPage";

function setup(initial: Parameters<typeof programApi>[0] = {}) {
  const api = programApi(initial);
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/apprendre/programme/:programId", element: <ProgramPage /> }],
    "/apprendre/programme/p1",
  );
  return { ...api, ...view };
}

const failure = (code: string, message: string, details: unknown = null) => ({
  error: { code, message, details },
});

describe("ProgramPage validation", () => {
  it("validates a draft and shows « Programme validé »", async () => {
    let called = 0;
    const { state, user } = setup();
    server.use(
      http.post(`${API}/programs/p1/validate`, () => {
        called += 1;
        state.program = programOut({ status: "validated" });
        return HttpResponse.json(
          { program_id: "p1", session_id: null, status: "validated" },
          { status: 202 },
        );
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Valider le programme" }));
    expect(await screen.findByText("Programme validé")).toBeInTheDocument();
    expect(called).toBe(1);
    expect(screen.getByText("Validé")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Valider le programme" })).toBeNull();
  });

  it("shows a refused validation (422) inline and keeps the draft", async () => {
    const { user } = setup();
    server.use(
      http.post(`${API}/programs/p1/validate`, () =>
        HttpResponse.json(
          failure("week_needs_quiz", "Semaine 2 : il manque un quiz en fin de semaine."),
          { status: 422 },
        ),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Valider le programme" }));
    expect(
      await screen.findByText("Semaine 2 : il manque un quiz en fin de semaine."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Valider le programme" })).toBeEnabled();
  });

  it("asks for a revision with a note, by resuming the validation question", async () => {
    let body: unknown = null;
    const { state, user } = setup();
    server.use(
      http.post(`${API}/sessions/s1/resume`, async ({ request }) => {
        body = await request.json();
        state.session = validationSession("running");
        return HttpResponse.json(state.session);
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Demander une révision" }));
    await user.type(screen.getByLabelText("Ce qu'il faut revoir"), "Moins de vidéos.");
    await user.click(screen.getByRole("button", { name: "Envoyer la demande" }));
    expect(await screen.findByText("Le Stratège met à jour le programme…")).toBeInTheDocument();
    expect(body).toEqual({
      interrupt_id: "i1",
      value: { action: "revise", note: "Moins de vidéos." },
    });
    expect(screen.queryByRole("button", { name: "Valider le programme" })).toBeNull();
  });

  it("refuses an empty revision note without calling the server", async () => {
    let called = false;
    const { user } = setup();
    server.use(
      http.post(`${API}/sessions/s1/resume`, () => {
        called = true;
        return HttpResponse.json(validationSession("running"));
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Demander une révision" }));
    await user.click(screen.getByRole("button", { name: "Envoyer la demande" }));
    expect(await screen.findByText("Dis ce qu'il faut revoir.")).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it("reads the program again when the revision finishes", async () => {
    const { state } = setup({ session: validationSession("running") });
    expect(await screen.findByText("Le Stratège met à jour le programme…")).toBeInTheDocument();
    state.session = validationSession("waiting_user");
    state.program = programOut({ version: 2, title: "Python pour la data (v2)" });
    expect(
      await screen.findByRole("heading", { name: "Python pour la data (v2)" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Demander une révision" }),
    ).toBeInTheDocument();
  }, 10_000);

  it("says a second « Valider » during a revision is not accepted, and reads the state", async () => {
    const { state, user } = setup();
    server.use(
      http.post(`${API}/programs/p1/validate`, () => {
        state.session = validationSession("paused");
        return HttpResponse.json(failure("program_not_waiting", "x", { status: "paused" }), {
          status: 409,
        });
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Valider le programme" }));
    expect(
      await screen.findByText(/Le programme n'attend pas de validation pour l'instant/),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Demander une révision" })).toBeNull(),
    );
  });

  it("validates a draft whose session is over, without offering a revision", async () => {
    setup({ session: validationSession("completed") });
    expect(await screen.findByRole("button", { name: "Valider le programme" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Demander une révision" })).toBeNull();
  });

  it("shows a validated program without validation buttons", async () => {
    setup({ program: programOut({ status: "validated" }) });
    expect(await screen.findByText("Programme validé")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Valider le programme" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Demander une révision" })).toBeNull();
  });
});
