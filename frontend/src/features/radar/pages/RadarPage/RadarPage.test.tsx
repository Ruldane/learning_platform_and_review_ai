import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { offerOut, radarRun, trendOut } from "@/test/radarApi";
import { renderRadar } from "@/test/radarHarness";
import { RadarPage } from "./RadarPage";

const setup = (api: Parameters<typeof renderRadar>[1] = {}, path?: string) =>
  renderRadar((createSocket) => <RadarPage createSocket={createSocket} />, api, path);

describe("RadarPage : résultat et historique", () => {
  it("shows the latest finished run: what was read, the ranking, the alerts and the offers", async () => {
    setup({
      runs: [
        radarRun("r2", {
          ranking: [
            trendOut("SQL", 1, 0.62, { delta_share: 8 }),
            trendOut("Rust", 2, 0.3, { new: true }),
            trendOut("Python", 3, 0.2, { delta_share: -2 }),
          ],
          alerts: [
            {
              skill: "Spark",
              share: 0.55,
              message: "Demandée dans 55 % des offres, absente de ton programme.",
            },
          ],
          offers: [offerOut("https://example.org/jobs/1", { score: 78 })],
          previous: { id: "r1", created_at: "2026-11-09T09:00:00Z" },
        }),
      ],
    });
    expect(await screen.findByText("47 offres lues · 6 bloquées · 41 analysées")).toBeVisible();
    const ranking = screen.getByRole("list", { name: "Classement des compétences" });
    expect(within(ranking).getByText("+8 pts")).toBeVisible();
    expect(within(ranking).getByText("nouvelle")).toBeVisible();
    expect(within(ranking).getByText("−2 pts")).toBeVisible();
    expect(
      screen.getByText(/Demandée dans 55 % des offres, absente de ton programme./),
    ).toBeVisible();
    expect(screen.getByText("score 78 sur 100")).toBeVisible();
    expect(screen.getByText("Bon match")).toBeVisible();
  });

  it("writes « premier relevé » when there is nothing to compare with", async () => {
    setup({ runs: [radarRun("r1", { ranking: [trendOut("SQL", 1, 0.62)] })] });
    expect(await screen.findByText("premier relevé")).toBeVisible();
  });

  it("warns about a reduced sample and says how many read offers were not analyzed", async () => {
    setup({
      runs: [radarRun("r1", { read_count: 18, analyzed: 12, low_sample: true, not_analyzed: 6 })],
    });
    expect(await screen.findByRole("note")).toHaveTextContent("Échantillon réduit");
    expect(screen.getByText("6 offres lues n'ont pas été analysées.")).toBeVisible();
    expect(screen.getByText(/18 offres lues/)).toBeVisible();
  });

  it("says why the latest run failed, in plain words", async () => {
    setup({
      runs: [radarRun("r3", { status: "failed", error_code: "search_unavailable", ranking: [] })],
    });
    const failure = (
      await screen.findByRole("heading", { name: "Ce relevé n'a pas abouti." })
    ).closest("section") as HTMLElement;
    expect(failure).toHaveTextContent(
      "Raison : la recherche d'offres n'a répondu à aucune requête, donc aucune offre n'a pu être lue.",
    );
    expect(screen.queryByText(/search_unavailable/)).toBeNull();
  });

  it("falls back to a general reason for an unknown error code", async () => {
    setup({ runs: [radarRun("r3", { status: "failed", error_code: "RuntimeError" })] });
    const failure = (
      await screen.findByRole("heading", { name: "Ce relevé n'a pas abouti." })
    ).closest("section") as HTMLElement;
    expect(failure).toHaveTextContent("Raison : une panne inattendue a interrompu le relevé.");
    const history = within(screen.getByRole("list", { name: "Relevés précédents" }));
    expect(history.getByText(/Raison : une panne inattendue/)).toBeVisible();
  });

  it("lists the history and opens an older run in place", async () => {
    const { user, router } = setup({
      runs: [
        radarRun("r3", {
          status: "failed",
          error_code: "session_cancelled",
          created_at: "2026-11-16T09:00:00Z",
        }),
        radarRun("r2", {
          created_at: "2026-11-09T09:00:00Z",
          read_count: 30,
          not_postings: 5,
          analyzed: 20,
          low_sample: true,
          role: "Analyste",
          ranking: [trendOut("Excel", 1, 0.8)],
        }),
      ],
    });
    const history = await screen.findByRole("list", { name: "Relevés précédents" });
    const rows = within(history).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("En échec");
    expect(rows[0]).toHaveTextContent("le relevé a été arrêté avant la fin");
    expect(rows[1]).toHaveTextContent("Terminé");
    expect(rows[1]).toHaveTextContent("25 lues · 6 bloquées · 20 analysées · échantillon réduit");
    expect(rows[0]).toHaveAttribute("aria-current", "true");

    await user.click(within(rows[1]!).getByRole("link"));
    expect(router.state.location.pathname).toBe("/carriere/radar/r2");
    expect(await screen.findByText("Excel")).toBeVisible();
    const after = within(await screen.findByRole("list", { name: "Relevés précédents" }));
    expect(after.getAllByRole("listitem")[1]).toHaveAttribute("aria-current", "true");
  });

  it("opens a run by its address, and says when it does not exist", async () => {
    setup(
      { runs: [radarRun("r1", { ranking: [trendOut("Excel", 1, 0.8)] })] },
      "/carriere/radar/zzz",
    );
    expect(await screen.findByRole("heading", { name: "Relevé introuvable" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Voir le radar" })).toBeVisible();
  });

  it("says the history is empty before any run", async () => {
    setup();
    expect(await screen.findByText("Aucun relevé pour l'instant.")).toBeVisible();
  });
});
