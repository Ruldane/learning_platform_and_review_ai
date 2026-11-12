import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DomainScoreView } from "../viewTypes";
import { SkillRadar } from "./SkillRadar";

const domains: DomainScoreView[] = [
  { domain: "Web", score: 72 },
  { domain: "Données", score: 35 },
  { domain: "Cloud", score: 0 },
];

describe("SkillRadar", () => {
  it("renders radar domains", () => {
    const { container } = render(<SkillRadar domains={domains} />);
    expect(container.querySelector(".recharts-radar")).not.toBeNull();
    for (const { domain } of domains) {
      expect(container.querySelector(".recharts-polar-angle-axis")).toHaveTextContent(domain);
    }
  });

  it("gives the same scores as text", () => {
    render(<SkillRadar domains={domains} />);
    const list = screen.getByRole("list", { name: "Score par domaine" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Web : 72 sur 100",
      "Données : 35 sur 100",
      "Cloud : 0 sur 100",
    ]);
  });

  it("scales the radius from 0 to 100", () => {
    const { container } = render(<SkillRadar domains={domains} />);
    const ticks = container.querySelectorAll(".recharts-polar-radius-axis .recharts-text");
    const labels = Array.from(ticks).map((tick) => tick.textContent);
    expect(labels).toContain("0");
    expect(labels).toContain("100");
  });

  it("names the chart for assistive technologies", () => {
    render(<SkillRadar domains={domains} />);
    expect(screen.getByRole("img", { name: "Radar par domaine" })).toBeInTheDocument();
  });

  it("says when there is no domain", () => {
    render(<SkillRadar domains={[]} />);
    expect(screen.getByText("Aucun domaine à afficher")).toBeInTheDocument();
  });
});
