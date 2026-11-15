import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FeedItem, SessionViewState } from "@/shared/realtime/types";
import type { Run } from "@/shared/realtime/useRun";
import { canAnswer, RunFeed } from "./RunFeed";

const question = (id = "q1"): Extract<FeedItem, { kind: "interrupt" }> => ({
  kind: "interrupt",
  seq: 2,
  answered: false,
  interrupt: {
    interrupt_id: id,
    kind: "choice",
    question: "Tu valides ?",
    options: [{ value: "yes", label: "Oui" }],
  },
});

/** Un `Run` minimal : seul ce que le fil lit. */
function fakeRun(over: Partial<SessionViewState> = {}, connection = "open", pending = false) {
  const resume = vi.fn().mockResolvedValue(true);
  const view = {
    status: "waiting_user",
    feed: [question()],
    pendingInterrupt: question().interrupt,
    cost: null,
    ...over,
  } as SessionViewState;
  const run = {
    stream: { status: view.status, connection, view },
    actions: { resume, pending, error: null },
    over: false,
  } as unknown as Run;
  return { run, resume };
}

describe("RunFeed", () => {
  it("shows the status bar and the common question card, and answers through the session", async () => {
    const user = userEvent.setup();
    const { run, resume } = fakeRun();
    render(<RunFeed run={run} label="Fil de la session" />);
    expect(screen.getByRole("region", { name: "Fil de la session" })).toBeVisible();
    expect(screen.getByText("Tu valides ?")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Oui" }));
    expect(resume).toHaveBeenCalledWith("q1", "yes");
  });

  it("uses the card the page gives, and the common one when it gives none", () => {
    const { run } = fakeRun();
    render(<RunFeed run={run} label="Fil" renderInterrupt={() => <p>Carte de la page</p>} />);
    expect(screen.getByText("Carte de la page")).toBeVisible();
    expect(screen.queryByText("Tu valides ?")).toBeNull();
  });

  it("says when the live feed is reconnecting", () => {
    const { run } = fakeRun({}, "reconnecting");
    render(<RunFeed run={run} label="Fil" />);
    expect(screen.getByText("Reconnexion au fil…")).toBeVisible();
  });

  it("does not let a question be answered twice while an answer is on its way", () => {
    const { run } = fakeRun({}, "open", true);
    render(<RunFeed run={run} label="Fil" />);
    expect(screen.getByRole("button", { name: "Oui" })).toBeDisabled();
  });
});

describe("canAnswer", () => {
  it("is true only for the open question when nothing is pending", () => {
    const item = question();
    expect(canAnswer(fakeRun().run, item)).toBe(true);
    expect(canAnswer(fakeRun().run, question("q2"))).toBe(false);
    expect(canAnswer(fakeRun({ status: "running" }).run, item)).toBe(false);
    expect(canAnswer(fakeRun({}, "open", true).run, item)).toBe(false);
  });
});
