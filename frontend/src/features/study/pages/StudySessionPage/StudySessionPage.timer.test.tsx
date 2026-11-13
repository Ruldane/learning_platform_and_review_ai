import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API } from "@/test/councilApi";
import { studyOut, summaryOut } from "@/test/studyApi";
import { recordPatches, renderStudySession } from "@/test/studyHarness";
import { finishedOut } from "@/test/studySessionKit";
import { server } from "@/test/server";
import { StudyTopbarSlot } from "../../StudyTopbarSlot";
import { StudySessionPage } from "./StudySessionPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const KEY = "study-timer:st1";
/** 40 minutes de travail gardées avant un rechargement de la page. */
const stored = { phase: "work", secondsLeft: 600, workedSeconds: 2400, running: true };

/** Le vrai minuteur (pas de faux) : seul ce qui est gardé dans `sessionStorage` compte. */
describe("StudySessionPage: minuteur gardé (revue finale 5)", () => {
  beforeEach(() => useSessionStore.getState().reset("s1"));
  afterEach(() => {
    useSessionStore.getState().reset("s1");
    window.sessionStorage.clear();
  });

  it("sends the time kept before a reload, without counting the interrupted time", async () => {
    window.sessionStorage.setItem(KEY, JSON.stringify(stored));
    const patches = recordPatches("/study-sessions/st1", 202, finishedOut());
    const { user } = renderStudySession(
      (createSocket) => <StudySessionPage createSocket={createSocket} pollMs={5} />,
      { sessions: [studyOut({ status: "interrupted" })] },
    );
    expect(await screen.findByText("Temps travaillé : 40 min")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reprendre" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Terminer" }));
    await waitFor(() => expect(patches).toEqual([{ action: "finish", worked_minutes: 40 }]));
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
    await waitFor(() => expect(window.sessionStorage.getItem(KEY)).toBeNull());
  });

  it("reads the summary again once the session is finished", async () => {
    let finished = false;
    // « Terminer » est accepté quand la session est encore ouverte ; le bilan arrive ensuite.
    let patched = false;
    server.use(
      http.patch(`${API}/study-sessions/st1`, () => {
        patched = true;
        return HttpResponse.json(studyOut({ session_id: null }), { status: 202 });
      }),
    );
    const { user } = renderStudySession(
      (createSocket) => (
        <>
          <StudyTopbarSlot />
          <StudySessionPage createSocket={createSocket} pollMs={5} />
        </>
      ),
      {
        summaryReply: () => HttpResponse.json(summaryOut({ week_minutes: finished ? 260 : 210 })),
        sessionReply: () => {
          if (!patched) return HttpResponse.json(studyOut({ status: "interrupted" }));
          finished = true;
          return HttpResponse.json(finishedOut());
        },
      },
    );
    expect(await screen.findByText("Cette semaine : 3 h 30")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Terminer" }));
    expect(await screen.findByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
    expect(await screen.findByText("Cette semaine : 4 h 20")).toBeInTheDocument();
  });
});
