import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { apiError, recordPosts } from "@/test/councilHarness";
import { studyOut } from "@/test/studyApi";
import { openStudyStream, recordPatches, renderStudySession } from "@/test/studyHarness";
import { finishedOut, tutorQuestion } from "@/test/studySessionKit";
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

/** Une session qui attend une réponse du Tuteur : « Terminer » est actif. */
async function waitingOnQuestion(api: Parameters<typeof renderStudySession>[1] = {}) {
  const view = setup({ status: "waiting_user", ...api });
  (await openStudyStream(view.fake)).push(tutorQuestion(councilEvents("s1")));
  return { ...view, finish: await screen.findByRole("button", { name: "Terminer" }) };
}

describe("StudySessionPage: Terminer", () => {
  beforeEach(() => useSessionStore.getState().reset("s1"));
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("finishes with the worked minutes through PATCH, never the generic resume", async () => {
    const resumes = recordPosts("/sessions/s1/resume", 202, {});
    const patches = recordPatches("/study-sessions/st1", 202, studyOut());
    const { fake, user } = setup({ status: "waiting_user", sessions: [studyOut(), finishedOut()] });
    const e = councilEvents("s1");
    (await openStudyStream(fake)).push(
      e.interrupt("finish_session", "i9", { question: "Veux-tu terminer la session ?" }),
    );
    await user.click(await screen.findByRole("button", { name: "Terminer la session" }));
    await waitFor(() => expect(patches).toEqual([{ action: "finish", worked_minutes: 2 }]));
    expect(resumes).toHaveLength(0);
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
  });

  it("also finishes from the header on a tutor question", async () => {
    const patches = recordPatches("/study-sessions/st1", 202, studyOut());
    const { user, finish } = await waitingOnQuestion({ sessions: [studyOut(), finishedOut()] });
    await user.click(finish);
    await waitFor(() => expect(patches).toEqual([{ action: "finish", worked_minutes: 2 }]));
    expect(await screen.findByText("Tu as compris les verbes HTTP.")).toBeInTheDocument();
  });

  it("shows the end summary once the tutor has written it", async () => {
    recordPatches("/study-sessions/st1", 202, studyOut());
    const { user, finish } = await waitingOnQuestion({
      sessions: [studyOut(), studyOut(), studyOut(), finishedOut()],
    });
    await user.click(finish);
    expect(await screen.findByText("Le tuteur rédige ton bilan…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
    expect(screen.getByText("Tu as compris les verbes HTTP.")).toBeInTheDocument();
    expect(screen.getByText("REST")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Réviser mes fiches" })).toHaveAttribute(
      "href",
      "/etudier/revisions",
    );
  });

  it("says when the summary takes too long and reads it again on request", async () => {
    recordPatches("/study-sessions/st1", 202, studyOut());
    const open = studyOut();
    const { user, finish } = await waitingOnQuestion({
      sessions: [...Array.from({ length: 22 }, () => open), finishedOut()],
    });
    await user.click(finish);
    expect(await screen.findByText(/Le bilan met du temps à arriver/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Relire le bilan" }));
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
  });

  it("shows a refused Terminer and lets the person try again", async () => {
    const patches = recordPatches(
      "/study-sessions/st1",
      409,
      apiError("study_not_waiting", "Le tuteur écrit encore.", { status: "running" }),
    );
    const { user, finish } = await waitingOnQuestion();
    await user.click(finish);
    expect(await screen.findByRole("alert")).toHaveTextContent("Le tuteur écrit encore.");
    expect(screen.getByRole("button", { name: "Terminer" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Terminer" }));
    await waitFor(() => expect(patches).toHaveLength(2));
  });

  it("sends Terminer once on a double click", async () => {
    const patches = recordPatches("/study-sessions/st1", 202, studyOut());
    const { user, finish } = await waitingOnQuestion();
    await user.dblClick(finish);
    await waitFor(() => expect(patches).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Terminer" })).toBeDisabled();
  });

  it("closes the composer once Terminer is accepted and never opens a dialog", async () => {
    const dialog = vi.spyOn(window, "confirm");
    recordPatches("/study-sessions/st1", 202, studyOut());
    const { user, finish } = await waitingOnQuestion();
    expect(await screen.findByLabelText("Ton message")).toBeEnabled();
    await user.click(finish);
    await waitFor(() => expect(screen.getByLabelText("Ton message")).toBeDisabled());
    expect(dialog).not.toHaveBeenCalled();
  });
});
