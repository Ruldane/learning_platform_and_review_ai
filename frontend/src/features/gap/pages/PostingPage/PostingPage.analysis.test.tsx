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
    expect(await screen.findByText("Analyzing…")).toBeInTheDocument();
    const stream = await openAnalysisStream(sockets);
    stream.push(councilEvents("a1").message("m1", "I am reading the posting.", "analyst"));
    expect(await screen.findByText("I am reading the posting.")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(screen.getByText("Analyzing…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieure données" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("This posting looks like one you've already added."),
    ).toBeVisible();
    expect(await screen.findByText("62/100")).toBeInTheDocument();
    const reads = state.reads.posting;
    await act(() => vi.advanceTimersByTimeAsync(12000));
    expect(state.reads.posting).toBe(reads);
  });

  it("stops after forty rereads, says so, and goes on when asked", async () => {
    const { user, state } = setup({ postings: [analyzing()] });
    expect(await screen.findByText("Analyzing…")).toBeInTheDocument();
    for (let poll = 0; poll < 45; poll += 1) {
      await act(() => vi.advanceTimersByTimeAsync(3000));
    }
    expect(
      await screen.findByText("The analysis is taking longer than expected."),
    ).toBeInTheDocument();
    expect(state.reads.posting).toBe(40);
    await user.click(screen.getByRole("button", { name: "Keep waiting" }));
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(state.reads.posting).toBeGreaterThan(40);
  });

  it("waits for the gap of a ready posting", async () => {
    setup({
      gaps: [gapOut({ status: "pending", score: null, rows: [], session_id: null }), gapOut()],
    });
    expect(await screen.findByText("Calculating the gap…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(await screen.findByText("62/100")).toBeInTheDocument();
  });
});
