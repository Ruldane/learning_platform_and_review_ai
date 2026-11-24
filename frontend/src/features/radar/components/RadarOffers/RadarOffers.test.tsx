import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { RadarOfferView } from "../viewTypes";
import { RadarOffers } from "./RadarOffers";

const offer = (over: Partial<RadarOfferView>): RadarOfferView => ({
  title: "Data engineer",
  company: "Exemple Tech",
  url: "https://example.org/jobs/1",
  score: 78,
  level: "mid_level",
  remote: null,
  salary: null,
  ...over,
});

function rowOf(title: string): HTMLElement {
  return screen.getByText(title).closest("li") as HTMLElement;
}

describe("RadarOffers", () => {
  it("shows a good match at scores of 70 and above", () => {
    render(
      <RadarOffers
        offers={[
          offer({}),
          offer({ title: "Analyste", url: "https://example.org/jobs/2", score: 70 }),
          offer({ title: "Chef de projet", url: "https://example.org/jobs/3", score: 69 }),
        ]}
      />,
    );
    expect(rowOf("Data engineer")).toHaveTextContent("score 78 out of 100");
    expect(within(rowOf("Data engineer")).getByText("Good match")).toBeInTheDocument();
    expect(within(rowOf("Analyste")).getByText("Good match")).toBeInTheDocument();
    expect(rowOf("Chef de projet")).toHaveTextContent("score 69 out of 100");
    expect(within(rowOf("Chef de projet")).queryByText("Good match")).toBeNull();
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
          offer({ remote: "partiel", salary: "45 000 à 55 000 €" }),
          offer({ title: "Sans détail", url: "https://example.org/jobs/9", level: "unknown" }),
        ]}
      />,
    );
    expect(rowOf("Data engineer")).toHaveTextContent(
      "Mid-level · Remote work: partiel · Stated salary: 45 000 à 55 000 €",
    );
    expect(rowOf("Sans détail")).not.toHaveTextContent("Stated salary");
    expect(rowOf("Sans détail")).not.toHaveTextContent("Unknown");
  });

  it("says there is no offer", () => {
    render(<RadarOffers offers={[]} />);
    expect(screen.getByText("No postings to show for this scan.")).toBeInTheDocument();
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
