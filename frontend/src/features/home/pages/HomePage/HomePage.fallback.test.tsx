import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream, renderHome } from "@/test/homeHarness";
import { HomePage } from "./HomePage";

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

// Le flux de la session reste muet (il a lâché) : seule la relecture de repli peut voir le conseil.
describe("HomePage : relecture de secours du conseil", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    useSessionStore.getState().reset("s9");
  });
  afterEach(() => vi.useRealTimers());

  it("re-reads a pending advice when the stream says nothing, shows it, then stops reading", async () => {
    const { sockets, state } = renderHome(
      (createSocket) => <HomePage createSocket={createSocket} />,
      { brief: { advice_status: "pending", advice: null, session_id: "s9" } },
    );
    expect(await screen.findByText("The council is meeting…")).toBeVisible();
    await openStream(sockets, "s9");

    const before = state.briefReads;
    await advance(15_500);
    expect(state.briefReads).toBeGreaterThan(before);
    expect(screen.getByText("The council is meeting…")).toBeVisible();

    state.brief = {
      ...state.brief,
      advice_status: "ready",
      advice: ["Phrase du conseil un.", "Phrase du conseil deux."],
      session_id: null,
    };
    await advance(15_500);
    expect(await screen.findByText("Phrase du conseil un.")).toBeVisible();
    expect(screen.queryByText("The council is meeting…")).toBeNull();

    const settled = state.briefReads;
    await advance(60_000);
    expect(state.briefReads).toBe(settled);
  });

  it("never re-reads an advice that is already final", async () => {
    const { state } = renderHome((createSocket) => <HomePage createSocket={createSocket} />, {
      brief: { advice_status: "unavailable", advice: null, session_id: null },
    });
    expect(
      await screen.findByText("The council had nothing to say this morning."),
    ).toBeVisible();
    await advance(60_000);
    expect(state.briefReads).toBe(1);
  });
});
