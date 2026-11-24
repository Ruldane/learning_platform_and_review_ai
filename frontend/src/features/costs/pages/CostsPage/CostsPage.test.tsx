import { screen, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { costsApi, costsReport, costRow } from "@/test/costsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { CostsPage } from "./CostsPage";

function setup(options: Parameters<typeof costsApi>[0] = {}) {
  const api = costsApi(options);
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/reglages/couts", element: <CostsPage /> }],
    "/reglages/couts",
  );
  return { ...api, ...view };
}

const table = (name: string) => screen.getByRole("table", { name });
describe("CostsPage", () => {
  it("costs page shows totals and four breakdowns", async () => {
    setup();
    await screen.findByRole("heading", { name: "Total over 30 days" });
    const totals = screen.getByRole("region", { name: "Total over 30 days" });
    expect(within(totals).getByText("$0.42")).toBeInTheDocument();
    expect(within(totals).getByText("12")).toBeInTheDocument();
    expect(within(totals).getByText("4,800")).toBeInTheDocument();
    expect(within(totals).getByText("1,360")).toBeInTheDocument();
    expect(within(totals).getByText("including 3 estimated")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /^Cost per day, from .*: \$0\.42 in total$/ }),
    ).toBeVisible();
    for (const name of [
      "Calls, tokens and cost per day",
      "By feature",
      "By agent",
      "By model",
    ]) {
      expect(table(name)).toBeInTheDocument();
    }
    expect(within(table("By model")).getByText("glm:glm-5.3-flash")).toBeInTheDocument();
  });

  it("names features, agents and keeps unknown names raw", async () => {
    setup();
    await screen.findByRole("table", { name: "By feature" });
    const features = within(table("By feature"));
    expect(
      features.getByRole("rowheader", { name: "Learning council" }),
    ).toBeInTheDocument();
    expect(features.getByRole("rowheader", { name: "No session" })).toBeInTheDocument();
    expect(features.getByRole("rowheader", { name: "Quiz" })).toBeInTheDocument();
    const agents = within(table("By agent"));
    expect(agents.getByRole("rowheader", { name: "Strategist" })).toBeInTheDocument();
    expect(agents.getByRole("rowheader", { name: "No agent" })).toBeInTheDocument();
  });

  it("shows both MCP clients with a cost of zero", async () => {
    setup({
      report: (days) =>
        costsReport(days, {
          by_model: [
            costRow("mcp:codex", { cost_usd: 0 }),
            costRow("mcp:claude-code", { cost_usd: 0 }),
          ],
        }),
    });
    const models = within(await screen.findByRole("table", { name: "By model" }));
    for (const name of ["Played by Codex", "Played by Claude"]) {
      const row = models.getByRole("row", { name: new RegExp(name) });
      expect(within(row).getByText("$0.00")).toBeInTheDocument();
    }
  });

  it("unknown graph shown raw", async () => {
    setup();
    await screen.findByRole("table", { name: "By feature" });
    expect(
      within(table("By feature")).getByRole("rowheader", { name: "mystery_graph" }),
    ).toBeInTheDocument();
    expect(
      within(table("By agent")).getByRole("rowheader", { name: "ghost_agent" }),
    ).toBeInTheDocument();
  });

  it("flags estimated calls in the rows", async () => {
    setup();
    await screen.findByRole("table", { name: "By feature" });
    const quiz = within(table("By feature")).getByRole("row", { name: /Quiz/ });
    expect(within(quiz).getAllByRole("cell").at(-1)).toHaveTextContent("1");
  });

  it("chart has a table alternative", async () => {
    setup();
    await screen.findByRole("table", { name: "Calls, tokens and cost per day" });
    const days = table("Calls, tokens and cost per day");
    // une ligne par jour de la fenêtre, plus l'en-tête
    expect(within(days).getAllByRole("row")).toHaveLength(31);
    expect(within(days).getByRole("columnheader", { name: "Cost" })).toBeInTheDocument();
    expect(within(days).getByRole("rowheader", { name: /16 Nov/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Cost per day/ })).toBeInTheDocument();
  });

  it("window change refetches", async () => {
    const { costRequests, user } = setup();
    await screen.findByRole("heading", { name: "Total over 30 days" });
    expect(costRequests.map((url) => url.searchParams.get("days"))).toEqual(["30"]);
    const thirty = screen.getByRole("button", { name: "30 days" });
    expect(thirty).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "7 days" }));
    await screen.findByRole("heading", { name: "Total over 7 days" });
    expect(costRequests.map((url) => url.searchParams.get("days"))).toEqual(["30", "7"]);
    expect(screen.getByRole("button", { name: "7 days" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "7 days" })).toHaveFocus();
    expect(within(table("Calls, tokens and cost per day")).getAllByRole("row")).toHaveLength(8);

    await user.click(screen.getByRole("button", { name: "90 days" }));
    await screen.findByRole("heading", { name: "Total over 90 days" });
    expect(costRequests.at(-1)?.searchParams.get("days")).toBe("90");
  });

  it("empty window shows empty state", async () => {
    const empty = (days: number) =>
      costsReport(days, {
        total: { calls: 0, tokens_in: 0, tokens_out: 0, cost_usd: 0, estimated_calls: 0 },
        by_feature: [],
        by_agent: [],
        by_model: [],
      });
    setup({ report: empty });
    await screen.findByRole("heading", { name: "No calls in the last 30 days" });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    // la fenêtre reste proposée : on peut en essayer une autre
    expect(screen.getByRole("button", { name: "90 days" })).toBeInTheDocument();
  });

  it("says when the costs cannot be read, and retries", async () => {
    let fails = true;
    const { user } = setup({
      report: (days) =>
        fails
          ? HttpResponse.json(
              { error: { code: "boom", message: "The server is unavailable.", details: null } },
              { status: 500 },
            )
          : costsReport(days),
    });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
    fails = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("heading", { name: "Total over 30 days" });
  });

  it("uses singular when one call is estimated", async () => {
    setup({
      report: (days) =>
        costsReport(days, {
          total: { calls: 5, tokens_in: 10, tokens_out: 5, cost_usd: 0.004, estimated_calls: 1 },
          by_feature: [costRow("quiz")],
        }),
    });
    await screen.findByText("including 1 estimated");
    expect(screen.getByText("$0.004")).toBeInTheDocument();
  });

  it("hides the estimated note when nothing is estimated", async () => {
    setup({
      report: (days) =>
        costsReport(days, {
          total: { calls: 5, tokens_in: 10, tokens_out: 5, cost_usd: 0.4, estimated_calls: 0 },
        }),
    });
    await screen.findByRole("heading", { name: "Total over 30 days" });
    expect(screen.queryByText(/including \d+ estimated/)).not.toBeInTheDocument();
  });
});
