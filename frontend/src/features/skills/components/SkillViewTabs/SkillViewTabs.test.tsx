import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SkillViewTabs } from "./SkillViewTabs";

describe("SkillViewTabs", () => {
  it("lists the four views and marks the current one", () => {
    render(<SkillViewTabs value="radar" onChange={() => undefined} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      "Graphe",
      "Radar",
      "Progression",
      "Comparaison",
    ]);
    expect(screen.getByRole("tab", { name: "Radar" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Graphe" })).toHaveAttribute("aria-selected", "false");
  });

  it("changes view on click", async () => {
    const onChange = vi.fn();
    render(<SkillViewTabs value="graph" onChange={onChange} />);
    await userEvent.click(screen.getByRole("tab", { name: "Progression" }));
    expect(onChange).toHaveBeenCalledWith("progress");
  });

  it("moves between views with the arrow keys, wrapping at the ends", async () => {
    const onChange = vi.fn();
    render(<SkillViewTabs value="graph" onChange={onChange} />);
    screen.getByRole("tab", { name: "Graphe" }).focus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(onChange).toHaveBeenLastCalledWith("compare");
    await userEvent.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenLastCalledWith("graph");
  });
});
