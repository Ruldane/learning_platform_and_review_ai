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
    await screen.findByRole("heading", { name: "Total sur 30 jours" });
    const totals = screen.getByRole("region", { name: "Total sur 30 jours" });
    expect(within(totals).getByText("0,42 $")).toBeInTheDocument();
    expect(within(totals).getByText("12")).toBeInTheDocument();
    expect(within(totals).getByText("4 800")).toBeInTheDocument();
    expect(within(totals).getByText("1 360")).toBeInTheDocument();
    expect(within(totals).getByText("dont 3 estimés")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /^Coût par jour, du .* : 0,42\s\$ au total$/ }),
    ).toBeVisible();
    for (const name of [
      "Appels, jetons et coût par jour",
      "Par feature",
      "Par agent",
      "Par modèle",
    ]) {
      expect(table(name)).toBeInTheDocument();
    }
    expect(within(table("Par modèle")).getByText("glm:glm-5.3-flash")).toBeInTheDocument();
  });

  it("names features, agents and keeps unknown names raw", async () => {
    setup();
    await screen.findByRole("table", { name: "Par feature" });
    const features = within(table("Par feature"));
    expect(
      features.getByRole("rowheader", { name: "Conseil d'apprentissage" }),
    ).toBeInTheDocument();
    expect(features.getByRole("rowheader", { name: "Hors session" })).toBeInTheDocument();
    expect(features.getByRole("rowheader", { name: "Quiz" })).toBeInTheDocument();
    const agents = within(table("Par agent"));
    expect(agents.getByRole("rowheader", { name: "Stratège" })).toBeInTheDocument();
    expect(agents.getByRole("rowheader", { name: "Sans agent" })).toBeInTheDocument();
  });

  it("affiche les deux clients MCP avec un coût nul", async () => {
    setup({
      report: (days) =>
        costsReport(days, {
          by_model: [
            costRow("mcp:codex", { cost_usd: 0 }),
            costRow("mcp:claude-code", { cost_usd: 0 }),
          ],
        }),
    });
    const models = within(await screen.findByRole("table", { name: "Par modèle" }));
    for (const name of ["Joué par Codex", "Joué par Claude"]) {
      const row = models.getByRole("row", { name: new RegExp(name) });
      expect(within(row).getByText("0,00 $")).toBeInTheDocument();
    }
  });

  it("unknown graph shown raw", async () => {
    setup();
    await screen.findByRole("table", { name: "Par feature" });
    expect(
      within(table("Par feature")).getByRole("rowheader", { name: "mystery_graph" }),
    ).toBeInTheDocument();
    expect(
      within(table("Par agent")).getByRole("rowheader", { name: "ghost_agent" }),
    ).toBeInTheDocument();
  });

  it("flags estimated calls in the rows", async () => {
    setup();
    await screen.findByRole("table", { name: "Par feature" });
    const quiz = within(table("Par feature")).getByRole("row", { name: /Quiz/ });
    expect(within(quiz).getAllByRole("cell").at(-1)).toHaveTextContent("1");
  });

  it("chart has a table alternative", async () => {
    setup();
    await screen.findByRole("table", { name: "Appels, jetons et coût par jour" });
    const days = table("Appels, jetons et coût par jour");
    // une ligne par jour de la fenêtre, plus l'en-tête
    expect(within(days).getAllByRole("row")).toHaveLength(31);
    expect(within(days).getByRole("columnheader", { name: "Coût" })).toBeInTheDocument();
    expect(within(days).getByRole("rowheader", { name: /16 nov/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Coût par jour/ })).toBeInTheDocument();
  });

  it("window change refetches", async () => {
    const { costRequests, user } = setup();
    await screen.findByRole("heading", { name: "Total sur 30 jours" });
    expect(costRequests.map((url) => url.searchParams.get("days"))).toEqual(["30"]);
    const thirty = screen.getByRole("button", { name: "30 jours" });
    expect(thirty).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "7 jours" }));
    await screen.findByRole("heading", { name: "Total sur 7 jours" });
    expect(costRequests.map((url) => url.searchParams.get("days"))).toEqual(["30", "7"]);
    expect(screen.getByRole("button", { name: "7 jours" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "7 jours" })).toHaveFocus();
    expect(within(table("Appels, jetons et coût par jour")).getAllByRole("row")).toHaveLength(8);

    await user.click(screen.getByRole("button", { name: "90 jours" }));
    await screen.findByRole("heading", { name: "Total sur 90 jours" });
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
    await screen.findByRole("heading", { name: "Aucun appel sur les 30 derniers jours" });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    // la fenêtre reste proposée : on peut en essayer une autre
    expect(screen.getByRole("button", { name: "90 jours" })).toBeInTheDocument();
  });

  it("says when the costs cannot be read, and retries", async () => {
    let fails = true;
    const { user } = setup({
      report: (days) =>
        fails
          ? HttpResponse.json(
              { error: { code: "boom", message: "Le serveur ne répond pas.", details: null } },
              { status: 500 },
            )
          : costsReport(days),
    });
    expect(await screen.findByText("Le serveur ne répond pas.")).toBeInTheDocument();
    fails = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    await screen.findByRole("heading", { name: "Total sur 30 jours" });
  });

  it("uses singular when one call is estimated", async () => {
    setup({
      report: (days) =>
        costsReport(days, {
          total: { calls: 5, tokens_in: 10, tokens_out: 5, cost_usd: 0.004, estimated_calls: 1 },
          by_feature: [costRow("quiz")],
        }),
    });
    await screen.findByText("dont 1 estimé");
    expect(screen.getByText("0,004 $")).toBeInTheDocument();
  });

  it("hides the estimated note when nothing is estimated", async () => {
    setup({
      report: (days) =>
        costsReport(days, {
          total: { calls: 5, tokens_in: 10, tokens_out: 5, cost_usd: 0.4, estimated_calls: 0 },
        }),
    });
    await screen.findByRole("heading", { name: "Total sur 30 jours" });
    expect(screen.queryByText(/dont/)).not.toBeInTheDocument();
  });
});
