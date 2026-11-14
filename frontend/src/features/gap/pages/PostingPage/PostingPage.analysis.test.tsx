import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { analyzingPosting, gapOut, postingOut } from "@/test/postingsApi";
import { openAnalysisStream, renderPosting } from "@/test/postingsHarness";
import { PostingPage } from "./PostingPage";

const analyzing = analyzingPosting;

function setup(api: Parameters<typeof renderPosting>[1] = {}) {
  return renderPosting((createSocket) => <PostingPage createSocket={createSocket} />, api);
}

describe("PostingPage while the posting is analysed", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("a1");
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    vi.useRealTimers();
    useSessionStore.getState().reset("a1");
  });

  it("follows the session, rereads every three seconds, then shows the result", async () => {
    const duplicate = {
      level: "possible",
      posting_id: "p7",
      title: "Ingénieur données",
      company: null,
      created_at: "2026-11-01T10:00:00Z",
    };
    const { sockets, state } = setup({
      postings: [analyzing(), analyzing(), postingOut({ duplicates: [duplicate] })],
    });
    expect(await screen.findByText("Analyse en cours…")).toBeInTheDocument();
    const stream = await openAnalysisStream(sockets);
    stream.push(councilEvents("a1").message("m1", "Je lis l'offre.", "analyst"));
    expect(await screen.findByText("Je lis l'offre.")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(screen.getByText("Analyse en cours…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieure données" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Cette offre ressemble à une offre déjà ajoutée."),
    ).toBeVisible();
    expect(await screen.findByText("62/100")).toBeInTheDocument();
    const reads = state.reads.posting;
    await act(() => vi.advanceTimersByTimeAsync(12000));
    expect(state.reads.posting).toBe(reads);
  });

  it("stops after forty rereads, says so, and goes on when asked", async () => {
    const { user, state } = setup({ postings: [analyzing()] });
    expect(await screen.findByText("Analyse en cours…")).toBeInTheDocument();
    for (let poll = 0; poll < 45; poll += 1) {
      await act(() => vi.advanceTimersByTimeAsync(3000));
    }
    expect(await screen.findByText("L'analyse prend plus de temps que prévu.")).toBeInTheDocument();
    expect(state.reads.posting).toBe(40);
    await user.click(screen.getByRole("button", { name: "Continuer à attendre" }));
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(state.reads.posting).toBeGreaterThan(40);
  });

  it("waits for the gap of a ready posting", async () => {
    setup({
      gaps: [gapOut({ status: "pending", score: null, rows: [], session_id: null }), gapOut()],
    });
    expect(await screen.findByText("Calcul de l'écart en cours…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(await screen.findByText("62/100")).toBeInTheDocument();
  });
});
