import { screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { apiError, recordPosts } from "@/test/councilHarness";
import { studyOut } from "@/test/studyApi";
import { openStudyStream, recordPatches, renderStudySession } from "@/test/studyHarness";
import { finishedOut, resumedSession, tutorOptions, tutorQuestion } from "@/test/studySessionKit";
import { StudySessionPage } from "./StudySessionPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));
// Le minuteur réel compte des secondes de mur : ce faux annonce 100 s de travail (2 min arrondies).
vi.mock("../../components/StudyTimer", async () => {
  const { useEffect } = await import("react");
  return {
    StudyTimer: ({ onWorkedChange }: { onWorkedChange: (seconds: number) => void }) => {
      useEffect(() => onWorkedChange(100));
      return <p>Minuteur de test</p>;
    },
  };
});

const setup = (api: Parameters<typeof renderStudySession>[1] = {}) =>
  renderStudySession(
    (createSocket) => <StudySessionPage createSocket={createSocket} pollMs={5} />,
    api,
  );

describe("StudySessionPage", () => {
  beforeEach(() => useSessionStore.getState().reset("s1"));
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("answers a tutor question with the typed text", async () => {
    const resumes = recordPosts("/sessions/s1/resume", 202, resumedSession);
    const { fake, user } = setup({ status: "waiting_user" });
    const e = councilEvents("s1");
    (await openStudyStream(fake)).push(
      e.message("t1", "Qu'est-ce qu'un verbe HTTP ?", "tutor"),
      tutorQuestion(e),
    );
    await user.type(await screen.findByLabelText("Ta réponse"), "Il lit une ressource");
    await user.click(screen.getByRole("button", { name: "Répondre" }));
    await waitFor(() =>
      expect(resumes).toEqual([
        { interrupt_id: "i1", value: { answers: { answer: "Il lit une ressource" } } },
      ]),
    );
  });

  it("sends the stuck value of the back, with its counted label", async () => {
    const resumes = recordPosts("/sessions/s1/resume", 202, resumedSession);
    const { fake, user } = setup({ status: "waiting_user" });
    (await openStudyStream(fake)).push(tutorQuestion(councilEvents("s1")));
    await user.click(await screen.findByRole("button", { name: "Je bloque (1/3)" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "i1", value: "stuck" }]));
  });

  it("sends the skip value of the back", async () => {
    const resumes = recordPosts("/sessions/s1/resume", 202, resumedSession);
    const { fake, user } = setup({ status: "waiting_user" });
    (await openStudyStream(fake)).push(tutorQuestion(councilEvents("s1")));
    await user.click(await screen.findByRole("button", { name: "Passer" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "i1", value: "skip" }]));
  });

  it("disables Terminer while the tutor writes", async () => {
    const { fake } = setup();
    const e = councilEvents("s1");
    const socket = await openStudyStream(fake);
    socket.push(e.started("tutor"));
    const finish = await screen.findByRole("button", { name: "Terminer" });
    expect(finish).toBeDisabled();
    expect(screen.getByText(/Le tuteur écrit/)).toBeInTheDocument();
    socket.push(
      e.interrupt("tutor_question", "i1", { question: "Que fait GET ?", options: tutorOptions }),
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "Terminer" })).toBeEnabled());
  });

  it("explains an interrupted session and keeps Terminer and a new start", async () => {
    const patches = recordPatches("/study-sessions/st1", 202, finishedOut());
    const { fake, user, router } = setup({ sessions: [studyOut({ status: "interrupted" })] });
    expect(await screen.findByText(/La session du tuteur s'est arrêtée/)).toBeInTheDocument();
    expect(fake.sockets).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: "Terminer" }));
    await waitFor(() => expect(patches).toEqual([{ action: "finish", worked_minutes: 2 }]));
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/etudier/session/st1");
  });

  it("offers a new block from an interrupted session", async () => {
    const { user, router } = setup({ sessions: [studyOut({ status: "interrupted" })] });
    await user.click(await screen.findByRole("button", { name: "Commencer un nouveau bloc" }));
    expect(router.state.location.pathname).toBe("/etudier/session");
  });

  it("reads the session again when the agents session fails", async () => {
    const { fake } = setup({
      status: "failed",
      sessions: [studyOut(), studyOut({ status: "interrupted" })],
    });
    (await openStudyStream(fake)).push(councilEvents("s1").failed());
    expect(await screen.findByText(/La session du tuteur s'est arrêtée/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Terminer" })).toBeEnabled();
  });

  it("shows the board of the tutor on the right", async () => {
    const { fake } = setup();
    (await openStudyStream(fake)).push(councilEvents("s1").boardUpdate("b1", 1));
    expect(await screen.findByRole("region", { name: "Tableau du tuteur" })).toBeInTheDocument();
    expect(await screen.findByText("Carte du domaine")).toBeInTheDocument();
  });

  it("shows the summary of a session that is already finished, without a stream", async () => {
    const { fake } = setup({ sessions: [finishedOut()] });
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
    expect(fake.sockets).toHaveLength(0);
  });

  it("says that a cancelled session wrote nothing", async () => {
    const { user, router } = setup({ sessions: [studyOut({ status: "cancelled" })] });
    expect(await screen.findByRole("heading", { name: "Session abandonnée" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Commencer un nouveau bloc" }));
    expect(router.state.location.pathname).toBe("/etudier/session");
  });

  it("has an empty state for an unknown session", async () => {
    const { user, router } = setup({
      sessionReply: () =>
        HttpResponse.json(apiError("study_session_not_found", "Session introuvable."), {
          status: 404,
        }),
    });
    expect(await screen.findByRole("heading", { name: "Session introuvable" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retour à la session guidée" }));
    expect(router.state.location.pathname).toBe("/etudier/session");
  });

  it("announces the loading, then shows an error with a retry button", async () => {
    let calls = 0;
    const { user } = setup({
      sessionReply: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 })
          : HttpResponse.json(finishedOut());
      },
    });
    expect(screen.getByRole("status")).toHaveTextContent("Ouverture de la session…");
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
  });
});
