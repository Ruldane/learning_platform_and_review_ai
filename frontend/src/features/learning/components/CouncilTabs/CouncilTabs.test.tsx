import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { CouncilTab } from "../viewTypes";
import { CouncilTabs } from "./CouncilTabs";

function Harness({
  initial = "board",
  onChange,
}: {
  initial?: CouncilTab;
  onChange?: (t: CouncilTab) => void;
}) {
  const [active, setActive] = useState<CouncilTab>(initial);
  return (
    <CouncilTabs
      active={active}
      onChange={(tab) => {
        onChange?.(tab);
        setActive(tab);
      }}
      board={<p>Contenu du tableau</p>}
      sources={<p>Contenu des sources</p>}
      proposals={<p>Contenu des propositions</p>}
    />
  );
}

describe("CouncilTabs", () => {
  it("is a tablist with three tabs and the active one selected", () => {
    render(<Harness />);
    expect(screen.getByRole("tablist", { name: "Espaces du Conseil" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
      "Tableau",
      "Sources",
      "Propositions",
    ]);
    expect(screen.getByRole("tab", { name: "Tableau" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Sources" })).toHaveAttribute("aria-selected", "false");
  });

  it("links each tab to its panel", () => {
    render(<Harness />);
    const tab = screen.getByRole("tab", { name: "Tableau" });
    const panel = screen.getByRole("tabpanel", { name: "Tableau" });
    expect(tab).toHaveAttribute("aria-controls", panel.id);
    expect(panel).toHaveAttribute("aria-labelledby", tab.id);
  });

  it("shows the panel of the active tab only", () => {
    render(<Harness initial="sources" />);
    expect(screen.getByText("Contenu des sources")).toBeVisible();
    expect(screen.queryByText("Contenu du tableau")).toBeNull();
  });

  it("keeps a panel mounted once it has been shown", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("tab", { name: "Sources" }));
    expect(screen.getByText("Contenu des sources")).toBeVisible();
    expect(screen.getByText("Contenu du tableau")).not.toBeVisible();
    expect(screen.queryByText("Contenu des propositions")).toBeNull();
  });

  it("changes tab on click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    await user.click(screen.getByRole("tab", { name: "Propositions" }));
    expect(onChange).toHaveBeenCalledWith("proposals");
  });

  it("supports arrow-key navigation", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    screen.getByRole("tab", { name: "Tableau" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenLastCalledWith("sources");
    expect(screen.getByRole("tab", { name: "Sources" })).toHaveFocus();
    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(onChange).toHaveBeenLastCalledWith("board");
    expect(screen.getByRole("tab", { name: "Tableau" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(onChange).toHaveBeenLastCalledWith("proposals");
    await user.keyboard("{Home}");
    expect(onChange).toHaveBeenLastCalledWith("board");
    await user.keyboard("{End}");
    expect(onChange).toHaveBeenLastCalledWith("proposals");
    expect(screen.getByRole("tab", { name: "Propositions" })).toHaveFocus();
  });

  it("only the selected tab is in the tab order", () => {
    render(<Harness />);
    expect(screen.getByRole("tab", { name: "Tableau" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Sources" })).toHaveAttribute("tabindex", "-1");
  });

  it("lets the page switch tab from outside", () => {
    const { rerender } = render(
      <CouncilTabs
        active="board"
        onChange={vi.fn()}
        board={<p>Contenu du tableau</p>}
        sources={<p>Contenu des sources</p>}
        proposals={<p>Contenu des propositions</p>}
      />,
    );
    rerender(
      <CouncilTabs
        active="proposals"
        onChange={vi.fn()}
        board={<p>Contenu du tableau</p>}
        sources={<p>Contenu des sources</p>}
        proposals={<p>Contenu des propositions</p>}
      />,
    );
    expect(screen.getByText("Contenu des propositions")).toBeVisible();
    expect(screen.getByRole("tab", { name: "Propositions" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
