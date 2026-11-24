import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { debriefOut, exchangeOut, interviewOut } from "@/test/interviewApi";
import { ask, SESSION, setup, startInterview } from "./interviewTestkit";

const past = (over: Record<string, unknown> = {}) => interviewOut({ id: "iv1", ...over });

describe("InterviewPage debrief", () => {
  beforeEach(() => useSessionStore.getState().reset(SESSION));

  it("replaces the feed with the debrief when the interview ends, and puts the focus on its title", async () => {
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    await screen.findByRole("region", { name: "Question 1 of 7" });
    view.interviews.finish("iv-new");
    stream.push(e.completed());
    const title = await screen.findByRole("heading", { level: 2, name: "Interview debrief" });
    await waitFor(() => expect(title).toHaveFocus());
    const scores = within(screen.getByRole("list", { name: "Your scores" }));
    expect(scores.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByRole("button", { name: "Start another interview" })).toBeVisible();
  });

  it("links the review cards to the Reviews page", async () => {
    const view = setup({ interviews: [past({ cards_created: 2 })] });
    await view.user.click(await screen.findByRole("button", { name: /Mixed, 15 minutes/ }));
    expect(
      await screen.findByText("2 review cards were created, to review tomorrow."),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Open my reviews" })).toHaveAttribute(
      "href",
      "/etudier/revisions",
    );
  });

  it("flags terms to check in the improved answer", async () => {
    const view = setup({ interviews: [past({ flags: ["Kubernetes"] })] });
    await view.user.click(await screen.findByRole("button", { name: /Mixed, 15 minutes/ }));
    expect(await screen.findByText("To check")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent("Kubernetes");
  });

  it("lists the past interviews of the application, opens one and comes back to the settings", async () => {
    const view = setup({
      interviews: [
        past({
          id: "iv2",
          mode: "technical",
          duration_min: 30,
          created_at: "2026-11-14T10:00:00Z",
        }),
        past({ id: "iv1", created_at: "2026-11-12T10:00:00Z" }),
        past({ id: "other", application_id: "a2" }),
      ],
    });
    const list = await screen.findByRole("list", { name: "Past interviews" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(within(list).getAllByRole("listitem")[0]).toHaveTextContent("Technical, 30 minutes");
    await view.user.click(within(list).getAllByRole("button")[0]!);
    expect(await screen.findByRole("heading", { name: "Interview debrief" })).toBeVisible();
    expect(screen.queryByRole("group", { name: "Format" })).toBeNull();
    await view.user.click(screen.getByRole("button", { name: "Back to settings" }));
    expect(await screen.findByRole("group", { name: "Format" })).toBeVisible();
    expect(screen.getByRole("list", { name: "Past interviews" })).toBeVisible();
  });

  it("follows the interview already running when the page opens, without the settings", async () => {
    const view = setup({
      interviews: [
        past({ id: "iv5", status: "running", session_id: "iv-s5", exchanges: [], debrief: null }),
      ],
    });
    const stream = await openStream(view.sockets, "iv-s5");
    stream.push(...ask(councilEvents("iv-s5"), 2, "q2", "Deuxième ?"));
    expect(await screen.findByRole("region", { name: "Question 2 of 4" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Start the interview" })).toBeNull();
  });

  it("says an interview stopped before any answer has nothing else", async () => {
    const view = setup({
      interviews: [past({ status: "stopped", exchanges: [], debrief: null, cards_created: 0 })],
    });
    await view.user.click(
      await screen.findByRole("button", { name: /Stopped before the first answer/ }),
    );
    expect(await screen.findByText(/You ended the interview before answering/)).toBeVisible();
    expect(screen.queryByRole("list", { name: "Your scores" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Open my reviews" })).toBeNull();
  });

  it("shows the answers and says the debrief could not be written when it failed", async () => {
    const view = setup({
      interviews: [
        past({
          status: "debrief_failed",
          debrief: null,
          cards_created: 0,
          exchanges: [exchangeOut(0, { answer: "Ma réponse gardée." })],
        }),
      ],
    });
    await view.user.click(await screen.findByRole("button", { name: /Debrief not written/ }));
    expect(await screen.findByText(/The debrief couldn't be written/)).toBeVisible();
    expect(screen.getByText("Ma réponse gardée.")).toBeVisible();
    expect(screen.queryByText(/Score:/)).toBeNull();
    expect(screen.queryByRole("list", { name: "Your scores" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Open my reviews" })).toBeNull();
  });

  it("says a session that ended without result did not rate anything", async () => {
    const view = setup({
      interviews: [past({ status: "failed", exchanges: [], debrief: null, cards_created: 0 })],
    });
    await view.user.click(await screen.findByRole("button", { name: /No result/ }));
    expect(await screen.findByText(/The interview stopped without a result/)).toBeVisible();
  });

  it("says which answers could not be rated", async () => {
    const view = setup({
      interviews: [
        past({
          debrief: debriefOut({ unrated: [0] }),
          exchanges: [exchangeOut(0, { unrated: true }), exchangeOut(1, { note: 2 })],
        }),
      ],
    });
    await view.user.click(await screen.findByRole("button", { name: /Mixed, 15 minutes/ }));
    expect(
      await screen.findByText(/The answer to question 1 couldn't be scored/),
    ).toBeVisible();
    expect(screen.getByText("Not scored")).toBeVisible();
  });

  it("keeps the debrief of an interview taken up on arrival when it ends, instead of going back to the settings", async () => {
    useSessionStore.getState().reset("iv-s5");
    const view = setup({
      interviews: [
        past({ id: "iv5", status: "running", session_id: "iv-s5", exchanges: [], debrief: null }),
      ],
    });
    const stream = await openStream(view.sockets, "iv-s5");
    const e = councilEvents("iv-s5");
    stream.push(...ask(e, 1, "q1", "Première ?"));
    await screen.findByRole("region", { name: "Question 1 of 4" });
    view.interviews.finish("iv5");
    stream.push(e.completed());
    const title = await screen.findByRole("heading", { name: "Interview debrief" });
    // The refreshed list marks the interview as finished and leaves the debrief open.
    await waitFor(() => expect(view.interviews.state.lists.length).toBeGreaterThan(1));
    expect(title).toBeVisible();
    expect(screen.queryByRole("button", { name: "Start the interview" })).toBeNull();
    expect(screen.getByRole("button", { name: "Start another interview" })).toBeVisible();
    await view.user.click(screen.getByRole("button", { name: "Start another interview" }));
    expect(await screen.findByRole("button", { name: "Start the interview" })).toBeVisible();
  });

  it("does not read the offers from the page of an application", async () => {
    const view = setup();
    await screen.findByRole("button", { name: "Start the interview" });
    expect(view.interviews.state.postingReads).toBe(0);
  });
});
