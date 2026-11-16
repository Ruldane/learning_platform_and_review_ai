import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { RadarOfferView } from "../viewTypes";
import { RadarOffers } from "./RadarOffers";

const offer = (over: Partial<RadarOfferView>): RadarOfferView => ({
  title: "Data engineer",
  company: "Exemple Tech",
  url: "https://example.org/jobs/1",
  score: 78,
  level: "confirme",
  remote: null,
  salary: null,
  ...over,
});

function rowOf(title: string): HTMLElement {
  return screen.getByText(title).closest("li") as HTMLElement;
}

describe("RadarOffers", () => {
  it("writes the score and marks 70 and above with the words « Bon match »", () => {
    render(
      <RadarOffers
        offers={[
          offer({}),
          offer({ title: "Analyste", url: "https://example.org/jobs/2", score: 70 }),
          offer({ title: "Chef de projet", url: "https://example.org/jobs/3", score: 69 }),
        ]}
      />,
    );
    expect(rowOf("Data engineer")).toHaveTextContent("score 78 sur 100");
    expect(within(rowOf("Data engineer")).getByText("Bon match")).toBeInTheDocument();
    expect(within(rowOf("Analyste")).getByText("Bon match")).toBeInTheDocument();
    expect(rowOf("Chef de projet")).toHaveTextContent("score 69 sur 100");
    expect(within(rowOf("Chef de projet")).queryByText("Bon match")).toBeNull();
  });

  it("opens each offer in a new tab without opener or referrer", () => {
    render(<RadarOffers offers={[offer({})]} />);
    const link = screen.getByRole("link", { name: /Data engineer/ });
    expect(link).toHaveAttribute("href", "https://example.org/jobs/1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows the company, level, remote work and a salary only when the offer states them", () => {
    render(
      <RadarOffers
        offers={[
          offer({ remote: "télétravail partiel", salary: "45 000 à 55 000 €", level: "senior" }),
          offer({ title: "Sans détail", url: "https://example.org/jobs/9", level: "inconnu" }),
        ]}
      />,
    );
    expect(rowOf("Data engineer")).toHaveTextContent(
      "Senior · télétravail partiel · Salaire indiqué : 45 000 à 55 000 €",
    );
    expect(rowOf("Sans détail")).not.toHaveTextContent("Salaire");
    expect(rowOf("Sans détail")).not.toHaveTextContent("Inconnu");
  });

  it("says there is no offer", () => {
    render(<RadarOffers offers={[]} />);
    expect(screen.getByText("Aucune offre à afficher pour ce relevé.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("lists two offers that share a link without a duplicate React key", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(
      <RadarOffers
        offers={[
          offer({ title: "Data engineer (Paris)" }),
          offer({ title: "Data engineer (Lyon)", score: 60 }),
        ]}
      />,
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Data engineer (Lyon)")).toBeInTheDocument();
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });
});
