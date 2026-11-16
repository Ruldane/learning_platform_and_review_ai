import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { OfferItemView } from "../viewTypes";
import { OffersCard } from "./OffersCard";

const ITEMS: OfferItemView[] = [
  { title: "Data engineer", company: "Exemple Tech", score: 78, url: "https://example.org/jobs/1" },
  { title: null, company: null, score: 71, url: "https://example.org/jobs/2" },
];

describe("OffersCard", () => {
  it("writes the score in words next to each offer", () => {
    render(<OffersCard items={ITEMS} />);
    expect(screen.getByText("score 78 sur 100")).toBeInTheDocument();
    expect(screen.getByText("score 71 sur 100")).toBeInTheDocument();
    expect(screen.getByText("Exemple Tech")).toBeInTheDocument();
    expect(screen.getByText("Offre sans titre")).toBeInTheDocument();
  });

  it("opens each offer on its own site, in a new tab, without opener or referrer", () => {
    render(<OffersCard items={ITEMS} />);
    const link = screen.getByRole("link", {
      name: "Data engineer (s'ouvre dans un nouvel onglet)",
    });
    expect(link).toHaveAttribute("href", "https://example.org/jobs/1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("never links an address that is not http or https", () => {
    render(
      <OffersCard
        items={[{ title: "Piège", company: null, score: 90, url: "javascript:alert(1)" }]}
      />,
    );
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Piège")).toBeInTheDocument();
  });

  it("says there is no new offer", () => {
    render(<OffersCard items={[]} />);
    expect(screen.getByText("Aucune nouvelle offre depuis ton dernier brief.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("lists two offers that share a link without a duplicate React key", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const same = "https://example.org/jobs/1";
    render(
      <OffersCard
        items={[
          { title: "Data engineer (Paris)", company: null, score: 78, url: same },
          { title: "Data engineer (Lyon)", company: null, score: 75, url: same },
        ]}
      />,
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("says the rubric is unavailable instead of « no new offer » when its source failed", () => {
    render(<OffersCard items={[]} unavailable />);
    expect(screen.getByText("Rubrique indisponible ce matin.")).toBeInTheDocument();
    expect(screen.queryByText("Aucune nouvelle offre depuis ton dernier brief.")).toBeNull();
  });
});
