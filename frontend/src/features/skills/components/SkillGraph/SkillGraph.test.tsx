import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LEVEL_COLORS } from "../levels";
import type { SkillEdgeView, SkillNodeView } from "../viewTypes";
import { SkillGraph } from "./SkillGraph";

const nodes: SkillNodeView[] = [
  { id: "s1", name: "HTML", domain: "web", level: "validated", demand: 0.9, evidenceCount: 3 },
  { id: "s2", name: "CSS", domain: "web", level: "in_progress", demand: null, evidenceCount: 1 },
  { id: "s3", name: "React", domain: "web", level: null, demand: 0.4, evidenceCount: 0 },
];
const edges: SkillEdgeView[] = [
  { beforeId: "s1", afterId: "s2" },
  { beforeId: "s2", afterId: "s3" },
];

function renderGraph(overrides: Partial<Parameters<typeof SkillGraph>[0]> = {}) {
  const onSelect = vi.fn();
  render(
    <SkillGraph nodes={nodes} edges={edges} selectedId={null} onSelect={onSelect} {...overrides} />,
  );
  return { onSelect };
}

describe("SkillGraph", () => {
  it("colors nodes by level with a legend", async () => {
    renderGraph();
    const html = await screen.findByRole("button", { name: "HTML: Validated" });
    expect(within(html).getByText("HTML").closest("[data-level]")).toHaveStyle({
      backgroundColor: LEVEL_COLORS.validated,
    });
    const css = await screen.findByRole("button", { name: "CSS: In progress" });
    expect(css.querySelector("[data-level]")).toHaveStyle({
      backgroundColor: LEVEL_COLORS.in_progress,
    });
    const react = await screen.findByRole("button", { name: "React: Missing" });
    expect(react.querySelector("[data-level]")).toHaveStyle({
      backgroundColor: LEVEL_COLORS.absent,
    });
    expect(screen.getByRole("list", { name: "Level legend" })).toBeInTheDocument();
  });

  it("writes the level in words inside each node", async () => {
    renderGraph();
    const html = await screen.findByRole("button", { name: "HTML: Validated" });
    expect(within(html).getByText("Validated")).toBeInTheDocument();
  });

  it("selects a node with Enter", async () => {
    const { onSelect } = renderGraph();
    const css = await screen.findByRole("button", { name: "CSS: In progress" });
    css.focus();
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("s2");
  });

  it("selects a node with Space and with a click", async () => {
    const { onSelect } = renderGraph();
    const html = await screen.findByRole("button", { name: "HTML: Validated" });
    html.focus();
    await userEvent.keyboard(" ");
    expect(onSelect).toHaveBeenLastCalledWith("s1");
    // `fireEvent` : `userEvent.click` envoie un `mousedown` sans `view`, que d3-zoom (le panoramique
    // de React Flow) ne sait pas lire dans jsdom.
    fireEvent.click(await screen.findByRole("button", { name: "React: Missing" }));
    expect(onSelect).toHaveBeenLastCalledWith("s3");
  });

  it("makes every node reachable with Tab", async () => {
    renderGraph();
    const buttons = await screen.findAllByRole("button", { name: /: / });
    expect(buttons).toHaveLength(3);
    for (const button of buttons) expect(button).toHaveAttribute("tabindex", "0");
  });

  it("marks the selected node", async () => {
    renderGraph({ selectedId: "s3" });
    const react = await screen.findByRole("button", { name: "React: Missing" });
    expect(react).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "CSS: In progress" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("is read only: nodes cannot be dragged", async () => {
    renderGraph();
    const html = await screen.findByRole("button", { name: "HTML: Validated" });
    const node = html.closest(".react-flow__node");
    expect(node).not.toBeNull();
    expect(node).not.toHaveClass("draggable");
  });

  it("explains the graph in a hint and names the region", async () => {
    renderGraph();
    expect(
      await screen.findByRole("region", { name: "Skill graph" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Enter opens the details/)).toBeInTheDocument();
  });

  it("says when there is no skill", () => {
    renderGraph({ nodes: [], edges: [] });
    expect(screen.getByText("No skills on the map")).toBeInTheDocument();
  });
});
