import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { committeeOut, diffOut } from "@/test/committeeApi";
import { councilEvents } from "@/test/councilEvents";
import { setup } from "./committeeTestkit";

describe("CommitteePage", () => {
  beforeEach(() => useSessionStore.getState().reset("cm-s1"));

  it("introduces the committee with the application, the permanent simulation banner and the way back", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Simulated hiring committee" }),
    ).toBeVisible();
    expect(await screen.findByText("Acme, Data engineer")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent("A simulation, not a prediction.");
    expect(screen.getByRole("link", { name: "Back to the application" })).toHaveAttribute(
      "href",
      "/applications/a1",
    );
    expect(await screen.findByText(/No committee for this posting/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Run the committee" })).toBeEnabled();
  });

  it("keeps the banner on every state of the page, results included", async () => {
    setup({ runs: [committeeOut()] });
    await screen.findByRole("tab", { name: "Verdict" });
    expect(screen.getByRole("note")).toHaveTextContent("A simulation, not a prediction.");
  });

  it("says a missing application in words, with a way back to the board", async () => {
    setup({}, {}, "/applications/zz/committee");
    expect(await screen.findByText("This application no longer exists.")).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Application not found" })).toBeVisible();
  });

  it("asks for an analysed offer when the application has none", async () => {
    setup({}, { posting_id: null });
    expect(await screen.findByText(/isn't linked to an analyzed posting/)).toBeVisible();
    expect(screen.queryByRole("button", { name: /committee/i })).toBeNull();
    expect(screen.getByRole("note")).toHaveTextContent("A simulation, not a prediction.");
  });

  it("opens on the latest committee: its debate on the left, three tabs on the right, the verdict first", async () => {
    const { sockets } = setup({ runs: [committeeOut()] });
    const stream = await openStream(sockets, "cm-s1");
    const e = councilEvents("cm-s1");
    stream.push(
      e.message("ats_reader-impression", "Le CV passe bien le tri.", "ats_reader"),
      e.message("moderator-synthese", "Voici la synthèse.", "moderator"),
    );
    const feed = await screen.findByRole("region", { name: "Committee debate" });
    expect(await within(feed).findByRole("article", { name: "ATS reader" })).toBeVisible();
    expect(within(feed).getByRole("article", { name: "Moderator" })).toBeVisible();

    const tabs = await screen.findAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Votes", "Verdict", "Before / after"]);
    expect(screen.getByRole("tab", { name: "Verdict" })).toHaveAttribute("aria-selected", "true");
    const panel = screen.getByRole("tabpanel", { name: "Verdict" });
    expect(within(panel).getByText("The committee says:")).toBeVisible();
    expect(within(panel).getByText("Yes")).toBeVisible();
    expect(within(panel).getByText("The votes were 3 yes, 1 no, and 0 maybe.")).toBeVisible();
  });

  it("nests its headings under the page title without skipping a level or doubling a region", async () => {
    setup({ runs: [committeeOut()] });
    await screen.findByRole("tab", { name: "Verdict" });
    expect(screen.getByRole("heading", { level: 2, name: "Committee verdict" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 3, name: /Objections/ })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Committee verdict" })).toBeNull();
    expect(screen.queryByRole("heading", { level: 4 })).toBeNull();
  });

  it("shows the four motivated votes with each main objection on the Votes tab, navigable by keyboard", async () => {
    const { user } = setup({ runs: [committeeOut()] });
    const verdict = await screen.findByRole("tab", { name: "Verdict" });
    verdict.focus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Votes" })).toHaveFocus();
    const panel = screen.getByRole("tabpanel", { name: "Votes" });
    const items = within(panel).getAllByRole("listitem");
    expect(items).toHaveLength(4);
    expect(items[2]).toHaveTextContent("Manager");
    expect(items[2]).toHaveTextContent("No");
    expect(items[2]).toHaveTextContent("Objection de manager.");
    expect(items[2]).toHaveTextContent("Raison de manager.");
  });

  it("ranks the objections and the three changes, one of which is to acquire, on the Verdict tab", async () => {
    setup({ runs: [committeeOut()] });
    const panel = await screen.findByRole("tabpanel", { name: "Verdict" });
    const objections = within(panel)
      .getByRole("heading", { name: /Objections/ })
      .parentElement!.querySelectorAll("li");
    expect(objections).toHaveLength(2);
    expect(objections[0]).toHaveTextContent("Peu de résultats chiffrés.");
    const changes = within(
      within(panel).getByRole("heading", { name: "Three changes to make" }).parentElement!,
    ).getAllByRole("listitem");
    expect(changes).toHaveLength(3);
    expect(within(changes[1]!).getByText("To acquire")).toBeVisible();
    expect(changes[1]).toHaveTextContent("Skills involved: Kubernetes");
    expect(within(changes[0]!).queryByText("To acquire")).toBeNull();
  });

  it("says the first committee has nothing to compare, then shows the before and after of the next", async () => {
    const first = setup({ runs: [committeeOut()] });
    await first.user.click(await screen.findByRole("tab", { name: "Before / after" }));
    expect(
      within(screen.getByRole("tabpanel", { name: "Before / after" })).getByText(
        /This is the first committee/,
      ),
    ).toBeVisible();
  });

  it("compares with the previous committee: votes before and after, objections gone and new", async () => {
    const { user } = setup({
      runs: [committeeOut({ id: "c2", previous: diffOut({ previous_id: "c1" }) }), committeeOut()],
    });
    await user.click(await screen.findByRole("tab", { name: "Before / after" }));
    const panel = screen.getByRole("tabpanel", { name: "Before / after" });
    const rows = within(within(panel).getByRole("table")).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent(/ATS reader.*No.*Yes.*More favorable/);
    expect(rows[1]).toHaveTextContent(/Recruiter.*Yes.*Yes.*Unchanged/);
    expect(within(panel).getByText("Mot clé Kubernetes absent.")).toBeVisible();
    expect(within(panel).getByText("Résumé trop long.")).toBeVisible();
  });

  it("says a failed committee ended without a verdict and offers to run it again", async () => {
    setup({
      runs: [
        committeeOut({ status: "failed", verdict: null, votes: [], objections: [], changes: [] }),
      ],
    });
    expect(
      await screen.findByText(/The committee stopped without a verdict\. You can rerun it\./),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Rerun the committee" })).toBeEnabled();
  });
});
