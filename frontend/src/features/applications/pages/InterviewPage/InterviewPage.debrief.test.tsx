import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { debriefOut, exchangeOut, interviewOut } from "@/test/interviewApi";
import { ask, SESSION, setup, startInterview } from "./interviewTestkit";

const past = (over: Record<string, unknown> = {}) => interviewOut({ id: "iv1", ...over });

describe("InterviewPage, débrief", () => {
  beforeEach(() => useSessionStore.getState().reset(SESSION));

  it("replaces the feed with the debrief when the interview ends, and puts the focus on its title", async () => {
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    await screen.findByRole("region", { name: "Question 1 sur 7" });
    view.interviews.finish("iv-new");
    stream.push(e.completed());
    const title = await screen.findByRole("heading", { level: 2, name: "Débrief de l'entretien" });
    await waitFor(() => expect(title).toHaveFocus());
    const scores = within(screen.getByRole("list", { name: "Tes notes" }));
    expect(scores.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByRole("button", { name: "Commencer un autre entretien" })).toBeVisible();
  });

  it("links the revision cards to the Révisions page", async () => {
    const view = setup({ interviews: [past({ cards_created: 2 })] });
    await view.user.click(await screen.findByRole("button", { name: /Mixte, 15 minutes/ }));
    expect(
      await screen.findByText("2 fiches de révision ont été créées, à revoir demain."),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Ouvrir mes révisions" })).toHaveAttribute(
      "href",
      "/etudier/revisions",
    );
  });

  it("flags the improved answer « à vérifier » with its terms", async () => {
    const view = setup({ interviews: [past({ flags: ["Kubernetes"] })] });
    await view.user.click(await screen.findByRole("button", { name: /Mixte, 15 minutes/ }));
    expect(await screen.findByText("À vérifier")).toBeVisible();
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
    const list = await screen.findByRole("list", { name: "Entretiens passés" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(within(list).getAllByRole("listitem")[0]).toHaveTextContent("Technique, 30 minutes");
    await view.user.click(within(list).getAllByRole("button")[0]!);
    expect(await screen.findByRole("heading", { name: "Débrief de l'entretien" })).toBeVisible();
    expect(screen.queryByRole("group", { name: "Formule" })).toBeNull();
    await view.user.click(screen.getByRole("button", { name: "Retour aux réglages" }));
    expect(await screen.findByRole("group", { name: "Formule" })).toBeVisible();
    expect(screen.getByRole("list", { name: "Entretiens passés" })).toBeVisible();
  });

  it("follows the interview already running when the page opens, without the settings", async () => {
    const view = setup({
      interviews: [
        past({ id: "iv5", status: "running", session_id: "iv-s5", exchanges: [], debrief: null }),
      ],
    });
    const stream = await openStream(view.sockets, "iv-s5");
    stream.push(...ask(councilEvents("iv-s5"), 2, "q2", "Deuxième ?"));
    expect(await screen.findByRole("region", { name: "Question 2 sur 4" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Commencer l'entretien" })).toBeNull();
  });

  it("says an interview stopped before any answer has nothing else", async () => {
    const view = setup({
      interviews: [past({ status: "stopped", exchanges: [], debrief: null, cards_created: 0 })],
    });
    await view.user.click(
      await screen.findByRole("button", { name: /Arrêté avant la première réponse/ }),
    );
    expect(await screen.findByText(/Tu as terminé l'entretien avant de répondre/)).toBeVisible();
    expect(screen.queryByRole("list", { name: "Tes notes" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Ouvrir mes révisions" })).toBeNull();
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
    await view.user.click(await screen.findByRole("button", { name: /Débrief non écrit/ }));
    expect(await screen.findByText(/Le débrief n'a pas pu être écrit/)).toBeVisible();
    expect(screen.getByText("Ma réponse gardée.")).toBeVisible();
    expect(screen.queryByText(/Note :/)).toBeNull();
    expect(screen.queryByRole("list", { name: "Tes notes" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Ouvrir mes révisions" })).toBeNull();
  });

  it("says a session that ended without result did not rate anything", async () => {
    const view = setup({
      interviews: [past({ status: "failed", exchanges: [], debrief: null, cards_created: 0 })],
    });
    await view.user.click(await screen.findByRole("button", { name: /Sans résultat/ }));
    expect(await screen.findByText(/L'entretien s'est arrêté sans résultat/)).toBeVisible();
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
    await view.user.click(await screen.findByRole("button", { name: /Mixte, 15 minutes/ }));
    expect(
      await screen.findByText(/La réponse à la question 1 n'a pas pu être notée/),
    ).toBeVisible();
    expect(screen.getByText("Non notée")).toBeVisible();
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
    await screen.findByRole("region", { name: "Question 1 sur 4" });
    view.interviews.finish("iv5");
    stream.push(e.completed());
    const title = await screen.findByRole("heading", { name: "Débrief de l'entretien" });
    // La liste est relue : l'entretien n'y est plus « en cours », le débrief reste.
    await waitFor(() => expect(view.interviews.state.lists.length).toBeGreaterThan(1));
    expect(title).toBeVisible();
    expect(screen.queryByRole("button", { name: "Commencer l'entretien" })).toBeNull();
    expect(screen.getByRole("button", { name: "Commencer un autre entretien" })).toBeVisible();
    await view.user.click(screen.getByRole("button", { name: "Commencer un autre entretien" }));
    expect(await screen.findByRole("button", { name: "Commencer l'entretien" })).toBeVisible();
  });

  it("does not read the offers from the page of an application", async () => {
    const view = setup();
    await screen.findByRole("button", { name: "Commencer l'entretien" });
    expect(view.interviews.state.postingReads).toBe(0);
  });
});
