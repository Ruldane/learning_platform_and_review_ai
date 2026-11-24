import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { committeeOut, runningCommittee } from "@/test/committeeApi";
import { councilEvents } from "@/test/councilEvents";
import { setup, SESSION } from "./committeeTestkit";

describe("CommitteePage, un comité qui délibère", () => {
  beforeEach(() => {
    useSessionStore.getState().reset(SESSION);
    useSessionStore.getState().reset("cm-s1");
  });

  it("starts the committee on the chosen version, follows its debate and announces that it deliberates", async () => {
    const view = setup();
    await view.user.click(await screen.findByRole("button", { name: "Run the committee" }));
    await waitFor(() => expect(view.committee.state.starts).toEqual([{ cv_version_id: "v1" }]));
    const stream = await openStream(view.sockets, SESSION);
    expect(await screen.findByText("The committee is deliberating…")).toHaveFocus();
    expect(screen.getByRole("button", { name: "Rerun the committee" })).toBeDisabled();
    expect(await screen.findByText("The committee is deliberating.")).toBeInTheDocument();

    const e = councilEvents(SESSION);
    stream.push(
      e.message("ats_reader-impression", "Je lis ce CV comme un logiciel.", "ats_reader"),
      e.message("recruiter-impression", "Parcours cohérent.", "recruiter"),
      e.message("manager-impression", "Je veux des résultats.", "manager"),
      e.message("colleague-impression", "Je me vois travailler avec elle.", "colleague"),
    );
    const feed = await screen.findByRole("region", { name: "Committee debate" });
    for (const name of ["Lecteur ATS", "Recruteur", "Manager", "Futur collègue"]) {
      expect(await within(feed).findByRole("article", { name })).toBeVisible();
    }
    // Tant que le comité délibère, aucun résultat : seule la phrase qui le dit.
    const panel = screen.getByRole("tabpanel", { name: "Verdict" });
    expect(
      within(panel).getByText(/The committee is deliberating: the votes, verdict/),
    ).toBeVisible();
    expect(within(panel).queryByText("The committee says:")).toBeNull();
  });

  it("shows the verdict, announces it and moves the focus to its title when the committee ends", async () => {
    const view = setup();
    await view.user.click(await screen.findByRole("button", { name: "Run the committee" }));
    const stream = await openStream(view.sockets, SESSION);
    await screen.findByText("The committee is deliberating…");

    view.committee.finish("c1-new");
    stream.push(councilEvents(SESSION).completed());

    expect(await screen.findByText("The committee says:")).toBeVisible();
    expect(await screen.findByText("The committee reached its verdict: Yes.")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Committee verdict" })).toHaveFocus(),
    );
    expect(screen.queryByText("The committee is deliberating…")).toBeNull();
    expect(screen.getByRole("button", { name: "Rerun the committee" })).toBeEnabled();
  });

  it("compares the new run with the previous finished one once it ends", async () => {
    const view = setup({ runs: [committeeOut({ id: "c0" })] });
    await view.user.click(await screen.findByRole("button", { name: "Rerun the committee" }));
    const stream = await openStream(view.sockets, SESSION);
    await screen.findByText("The committee is deliberating…");
    view.committee.finish("c2-new");
    stream.push(councilEvents(SESSION).completed());
    await screen.findByText("The committee says:");
    await view.user.click(screen.getByRole("tab", { name: "Before / after" }));
    const panel = screen.getByRole("tabpanel", { name: "Before / after" });
    expect(await within(panel).findByRole("table")).toBeVisible();
    expect(within(panel).getByText("Résumé trop long.")).toBeVisible();
  });

  it("reads the committee again at the end of the session even when no event told the page", async () => {
    const view = setup({ runs: [runningCommittee({ id: "c1", session_id: "cm-s1" })] });
    const stream = await openStream(view.sockets, "cm-s1");
    expect(await screen.findByText("The committee is deliberating…")).not.toHaveFocus();
    view.committee.finish("c1");
    stream.push(councilEvents("cm-s1").completed());
    expect(await screen.findByText("The committee says:")).toBeVisible();
  });

  it("follows a committee that is already running when the page opens, without starting another", async () => {
    const view = setup({ runs: [runningCommittee({ id: "c1", session_id: "cm-s1" })] });
    await openStream(view.sockets, "cm-s1");
    expect(await screen.findByText("The committee is deliberating…")).toBeVisible();
    expect(view.committee.state.starts).toEqual([]);
    expect(screen.getByRole("button", { name: "Rerun the committee" })).toBeDisabled();
  });

  it("does not announce a committee that was already finished when the page opened", async () => {
    setup({ runs: [committeeOut()] });
    await screen.findByText("The committee says:");
    expect(screen.queryByText(/The committee reached its verdict/)).toBeNull();
    expect(screen.getByRole("heading", { name: "Committee verdict" })).not.toHaveFocus();
  });
});
