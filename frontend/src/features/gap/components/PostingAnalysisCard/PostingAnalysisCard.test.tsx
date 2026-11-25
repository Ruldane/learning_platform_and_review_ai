import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PostingAnalysisView } from "../viewTypes";
import { PostingAnalysisCard } from "./PostingAnalysisCard";

const analysis: PostingAnalysisView = {
  title: "Développeuse front",
  company: "Société Fictive",
  level: "mid_level",
  location: "Lyon",
  remote: "2 jours par semaine",
  requirements: [
    { text: "React", required: true },
    { text: "Accessibilité", required: false },
  ],
  keywords: ["React", "TypeScript"],
  eliminatory: ["Permis B"],
  tools: ["Git"],
};

describe("PostingAnalysisCard", () => {
  it("shows what the analysis understood", () => {
    render(<PostingAnalysisCard analysis={analysis} />);
    const card = screen.getByRole("region", { name: "Posting analysis" });
    expect(within(card).getByRole("heading", { name: "Développeuse front" })).toBeInTheDocument();
    for (const text of [
      "Company: Société Fictive",
      "Level: Mid-level",
      "Location: Lyon",
      "Remote work: 2 jours par semaine",
      "Permis B",
      "TypeScript",
      "Git",
    ]) {
      expect(within(card).getByText(text)).toBeInTheDocument();
    }
    expect(within(card).getByText("Required")).toBeInTheDocument();
    expect(within(card).getByText("Preferred")).toBeInTheDocument();
  });

  it("skips what is unknown", () => {
    render(
      <PostingAnalysisCard
        analysis={{
          ...analysis,
          company: null,
          location: null,
          remote: null,
          level: "unknown",
          eliminatory: [],
          tools: [],
          keywords: [],
          requirements: [],
        }}
      />,
    );
    expect(screen.getByText("Level: Level not specified")).toBeInTheDocument();
    expect(screen.queryByText(/Company/)).not.toBeInTheDocument();
    expect(screen.queryByText("Deal-breakers")).not.toBeInTheDocument();
    expect(screen.getByText("No requirements found.")).toBeInTheDocument();
  });

  it("leaves the title out when the page already shows it", () => {
    render(<PostingAnalysisCard analysis={analysis} showTitle={false} />);
    expect(screen.queryByRole("heading", { name: "Développeuse front" })).toBeNull();
    expect(screen.getByText("Company: Société Fictive")).toBeInTheDocument();
  });

  it("renders the offer text as plain text, never as markup", () => {
    render(
      <PostingAnalysisCard
        analysis={{ ...analysis, title: "<img src=x> Dev", keywords: ["<b>x</b>"] }}
      />,
    );
    expect(screen.getByRole("heading", { name: "<img src=x> Dev" })).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByText("<b>x</b>")).toBeInTheDocument();
  });
});
