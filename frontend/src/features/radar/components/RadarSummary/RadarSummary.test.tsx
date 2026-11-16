import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { RunSummaryView } from "../viewTypes";
import { RadarSummary } from "./RadarSummary";

const RUN: RunSummaryView = {
  role: "Data engineer",
  zone: "France",
  readCount: 47,
  blockedCount: 6,
  analyzed: 41,
  notPostings: 0,
  notAnalyzed: 0,
  blockedDomains: [
    { domain: "example.org", count: 4 },
    { domain: "example.invalid", count: 1 },
  ],
  lowSample: false,
};

describe("RadarSummary", () => {
  it("says how many offers were really read, blocked and analyzed", () => {
    render(<RadarSummary run={RUN} />);
    expect(screen.getByText("47 offres lues · 6 bloquées · 41 analysées")).toBeInTheDocument();
    expect(screen.getByText("Poste : Data engineer, zone : France")).toBeInTheDocument();
  });

  it("counts only the postings as offers read, the other pages are said apart", () => {
    render(<RadarSummary run={{ ...RUN, readCount: 35, notPostings: 7, analyzed: 28 }} />);
    expect(screen.getByText("28 offres lues · 6 bloquées · 28 analysées")).toBeInTheDocument();
    expect(screen.getByText("7 pages lues n'étaient pas des offres.")).toBeInTheDocument();
  });

  it("uses the singular", () => {
    render(<RadarSummary run={{ ...RUN, readCount: 1, blockedCount: 1, analyzed: 1 }} />);
    expect(screen.getByText("1 offre lue · 1 bloquée · 1 analysée")).toBeInTheDocument();
  });

  it("keeps the blocked domains folded until they are opened (the summary takes focus with Tab)", async () => {
    const user = userEvent.setup();
    render(<RadarSummary run={RUN} />);
    const summary = screen.getByText("Domaines bloqués (2)");
    const details = summary.closest("details") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    await user.tab();
    expect(summary).toHaveFocus();
    await user.click(summary);
    expect(details.open).toBe(true);
    expect(screen.getByText("example.org : 4 pages")).toBeVisible();
    expect(screen.getByText("example.invalid : 1 page")).toBeVisible();
  });

  it("shows no blocked domain block when none was blocked", () => {
    render(<RadarSummary run={{ ...RUN, blockedCount: 0, blockedDomains: [] }} />);
    expect(screen.queryByText(/Domaines bloqués/)).toBeNull();
  });

  it("warns about a small sample and only then", () => {
    const { rerender } = render(<RadarSummary run={RUN} />);
    expect(screen.queryByRole("note")).toBeNull();
    rerender(<RadarSummary run={{ ...RUN, lowSample: true }} />);
    expect(screen.getByRole("note")).toHaveTextContent("Échantillon réduit : moins de 30 offres");
  });

  it("counts the pages that were not postings apart", () => {
    render(<RadarSummary run={{ ...RUN, notPostings: 3 }} />);
    expect(screen.getByText("3 pages lues n'étaient pas des offres.")).toBeInTheDocument();
  });

  it("never hides the gap between the offers read and the offers analyzed", () => {
    const { rerender } = render(<RadarSummary run={{ ...RUN, notAnalyzed: 5 }} />);
    expect(screen.getByText("5 offres lues n'ont pas été analysées.")).toBeInTheDocument();
    rerender(<RadarSummary run={{ ...RUN, notAnalyzed: 1 }} />);
    expect(screen.getByText("1 offre lue n'a pas été analysée.")).toBeInTheDocument();
    rerender(<RadarSummary run={RUN} />);
    expect(screen.queryByText(/n'a pas été analysée|n'ont pas été analysées/)).toBeNull();
  });
});
