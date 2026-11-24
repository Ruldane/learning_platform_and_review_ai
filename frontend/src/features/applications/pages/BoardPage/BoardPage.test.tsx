import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { applicationOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { apiError } from "@/test/councilHarness";
import { expectCoherentOutline } from "@/test/headingOutline";
import { applicationsManifest } from "../../manifest";

const routes = applicationsManifest.routes;

const ROWS = () => [
  applicationOut({ id: "a1", company: "Acme", title: "Data engineer", status: "applied" }),
  applicationOut({
    id: "a2",
    company: "Beta",
    title: "Analyste",
    status: "to_apply",
    applied_on: null,
    next_action: null,
    next_action_on: null,
    due_reminders: 0,
  }),
  applicationOut({ id: "a3", company: "Gamma", title: "Chef de projet", status: "interview" }),
];

function setup(api: Parameters<typeof renderApplications>[2] = {}) {
  return renderApplications(routes, "/applications", { applications: ROWS(), ...api });
}

describe("BoardPage", () => {
  it("has one h1 per page, then the eight columns as h2 (one h1 per applications page)", async () => {
    setup();
    await screen.findByRole("group", { name: "Applied, 1" });
    expectCoherentOutline();
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(8);
    expect(screen.queryByRole("heading", { level: 3 })).toBeNull();
  });

  it("keeps the horizontal scroll inside the board: the page never scrolls sideways (kanban fits 1024 px)", async () => {
    setup();
    const board = await screen.findByRole("group", { name: "Application tracking board" });
    expect(board).toHaveClass("overflow-x-auto", "max-w-full", "min-w-0");
    // The board owns horizontal scrolling.
    const page = board.parentElement as HTMLElement;
    expect(page.className).not.toMatch(/overflow-x-(auto|scroll)/);
    expect(page).toHaveClass("min-w-0");
    expect(page.closest("main")?.className ?? "").not.toMatch(/overflow-x/);
  });

  it("shows the indicators and the cards in the column of their status", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Applications" })).toBeVisible();
    const applied = await screen.findByRole("group", { name: "Applied, 1" });
    expect(within(applied).getByText("Acme")).toBeVisible();
    expect(
      within(screen.getByRole("group", { name: "Interview, 1" })).getByText("Gamma"),
    ).toBeVisible();
    expect(
      await screen.findByRole("region", { name: "Application metrics" }),
    ).toBeVisible();
  });

  it("moves a card with the menu: posts a status event and the card changes column", async () => {
    const { user, state } = setup();
    await user.click(await screen.findByRole("button", { name: "Move “Analyste” (Beta)" }));
    await user.click(screen.getByRole("menuitem", { name: "Offer" }));
    expect(state.events).toEqual([{ id: "a2", body: { kind: "status", status: "offer" } }]);
    const offer = await screen.findByRole("group", { name: "Offer, 1" });
    expect(within(offer).getByText("Beta")).toBeVisible();
    expect(screen.getByRole("group", { name: "To apply, 0" })).toBeVisible();
  });

  it("gives the focus back to the moved card", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Move “Analyste” (Beta)" }));
    await user.click(screen.getByRole("menuitem", { name: "Offer" }));
    await screen.findByRole("group", { name: "Offer, 1" });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Move “Analyste” (Beta)" })).toHaveFocus(),
    );
  });

  it("puts the card back and says so when the server refuses the move", async () => {
    const { user } = setup({
      event: () =>
        HttpResponse.json(apiError("validation_error", "This status is not allowed."), {
          status: 422,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Move “Analyste” (Beta)" }));
    await user.click(screen.getByRole("menuitem", { name: "Offer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This status is not allowed.");
    await waitFor(() => expect(screen.getByRole("group", { name: "To apply, 1" })).toBeVisible());
    expect(screen.getByRole("group", { name: "Offer, 0" })).toBeVisible();
  });

  it("switches to the table, sorts it and keeps one row per application", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Table" }));
    expect(screen.getByRole("button", { name: "Table" })).toHaveAttribute("aria-pressed", "true");
    const table = await screen.findByRole("table", { name: "Applications" });
    expect(within(table).getAllByRole("row")).toHaveLength(4);
    await user.click(screen.getByRole("button", { name: "Sort by Company" }));
    await user.click(screen.getByRole("button", { name: "Sort by Company" }));
    const first = within(within(table).getAllByRole("row")[1]!).getAllByRole("cell")[0]!;
    expect(first).toHaveTextContent("Gamma");
  });

  it("opens the application drawer above the board when a card is opened", async () => {
    const { user, router } = setup();
    await user.click(
      await screen.findByRole("button", { name: "Open the Acme application, Data engineer role" }),
    );
    expect(router.state.location.pathname).toBe("/applications/a1");
    expect(await screen.findByRole("dialog", { name: /Acme, Data engineer/ })).toBeVisible();
    // The board stays mounted behind the modal drawer.
    expect(screen.getByRole("group", { name: "Applied, 1", hidden: true })).toBeInTheDocument();
  });

  it("offers to create the first application when there is none", async () => {
    const { user, router } = setup({ applications: [] });
    expect(await screen.findByText("No applications yet")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "New application" }));
    expect(router.state.location.pathname).toBe("/applications/new");
  });

  it("links to the new application page", async () => {
    const { user, router } = setup();
    await user.click(await screen.findByRole("link", { name: "New application" }));
    expect(router.state.location.pathname).toBe("/applications/new");
  });

  it("says it is loading, then shows the board", async () => {
    setup();
    expect(screen.getByText("Loading applications…")).toBeVisible();
    expect(await screen.findByRole("group", { name: "Applied, 1" })).toBeVisible();
  });

  it("shows an error with a retry when the list cannot be read", async () => {
    let calls = 0;
    const { user } = setup({
      list: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("internal_error", "The server is not responding."), {
              status: 500,
            })
          : HttpResponse.json(ROWS());
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is not responding.");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("group", { name: "Applied, 1" })).toBeVisible();
  });
});
