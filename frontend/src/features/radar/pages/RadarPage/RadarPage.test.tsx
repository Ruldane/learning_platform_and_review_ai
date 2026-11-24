import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { offerOut, radarRun, trendOut } from "@/test/radarApi";
import { renderRadar } from "@/test/radarHarness";
import { RadarPage } from "./RadarPage";

const setup = (api: Parameters<typeof renderRadar>[1] = {}, path?: string) =>
  renderRadar((createSocket) => <RadarPage createSocket={createSocket} />, api, path);

describe("RadarPage results and history", () => {
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
    expect(await screen.findByText("47 postings read · 6 blocked · 41 analyzed")).toBeVisible();
    const ranking = screen.getByRole("list", { name: "Skills ranking" });
    expect(within(ranking).getByText("+8 pts")).toBeVisible();
    expect(within(ranking).getByText("new")).toBeVisible();
    expect(within(ranking).getByText("−2 pts")).toBeVisible();
    expect(
      screen.getByText(/Demandée dans 55 % des offres, absente de ton programme./),
    ).toBeVisible();
    expect(screen.getByText("score 78 out of 100")).toBeVisible();
    expect(screen.getByText("Good match")).toBeVisible();
  });

  it("marks the first scan when there is nothing to compare with", async () => {
    setup({ runs: [radarRun("r1", { ranking: [trendOut("SQL", 1, 0.62)] })] });
    expect(await screen.findByText("first scan")).toBeVisible();
  });

  it("warns about a reduced sample and says how many read offers were not analyzed", async () => {
    setup({
      runs: [radarRun("r1", { read_count: 18, analyzed: 12, low_sample: true, not_analyzed: 6 })],
    });
    expect(await screen.findByRole("note")).toHaveTextContent("Small sample");
    expect(screen.getByText("6 postings read weren’t analyzed.")).toBeVisible();
    expect(screen.getByText(/18 postings read/)).toBeVisible();
  });

  it("says why the latest run failed, in plain words", async () => {
    setup({
      runs: [radarRun("r3", { status: "failed", error_code: "search_unavailable", ranking: [] })],
    });
    const failure = (
      await screen.findByRole("heading", { name: "This scan didn’t complete." })
    ).closest("section") as HTMLElement;
    expect(failure).toHaveTextContent(
      "Reason: the job search didn’t answer any request, so no postings could be read.",
    );
    expect(screen.queryByText(/search_unavailable/)).toBeNull();
  });

  it("says that the offers read could not be analysed when the run failed on analysis", async () => {
    setup({
      runs: [radarRun("r3", { status: "failed", error_code: "analysis_failed", ranking: [] })],
    });
    const failure = (
      await screen.findByRole("heading", { name: "This scan didn’t complete." })
    ).closest("section") as HTMLElement;
    expect(failure).toHaveTextContent("the postings read couldn’t be analyzed");
    expect(screen.queryByText(/analysis_failed/)).toBeNull();
  });

  it("falls back to a general reason for an unknown error code", async () => {
    setup({ runs: [radarRun("r3", { status: "failed", error_code: "RuntimeError" })] });
    const failure = (
      await screen.findByRole("heading", { name: "This scan didn’t complete." })
    ).closest("section") as HTMLElement;
    expect(failure).toHaveTextContent("Reason: an unexpected failure interrupted the scan.");
    const history = within(screen.getByRole("list", { name: "Previous scans" }));
    expect(history.getByText(/Reason: an unexpected failure/)).toBeVisible();
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
    const history = await screen.findByRole("list", { name: "Previous scans" });
    const rows = within(history).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Failed");
    expect(rows[0]).toHaveTextContent("the scan was stopped before the end");
    expect(rows[1]).toHaveTextContent("Done");
    expect(rows[1]).toHaveTextContent("25 read · 6 blocked · 20 analyzed · small sample");
    expect(rows[0]).toHaveAttribute("aria-current", "true");

    await user.click(within(rows[1]!).getByRole("link"));
    expect(router.state.location.pathname).toBe("/career/radar/r2");
    expect(await screen.findByText("Excel")).toBeVisible();
    const after = within(await screen.findByRole("list", { name: "Previous scans" }));
    expect(after.getAllByRole("listitem")[1]).toHaveAttribute("aria-current", "true");
  });

  it("opens a run by its address, and says when it does not exist", async () => {
    setup(
      { runs: [radarRun("r1", { ranking: [trendOut("Excel", 1, 0.8)] })] },
      "/career/radar/zzz",
    );
    expect(await screen.findByRole("heading", { name: "Scan not found" })).toBeVisible();
    expect(screen.getByRole("button", { name: "See the radar" })).toBeVisible();
  });

  it("says the history is empty before any run", async () => {
    setup();
    expect(await screen.findByText("No scans yet.")).toBeVisible();
  });
});
