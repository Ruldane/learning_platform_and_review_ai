import { describe, expect, it } from "vitest";
import { DEFAULT_DEMAND, layoutGraph, nodeSize } from "./layoutGraph";
import type { SkillEdgeView, SkillNodeView } from "./viewTypes";

function skill(id: string, demand: number | null = null): SkillNodeView {
  return { id, name: id, domain: "web", level: null, demand, evidenceCount: 0 };
}

const edge = (beforeId: string, afterId: string): SkillEdgeView => ({ beforeId, afterId });

describe("layoutGraph", () => {
  it("lays out prerequisites left to right", async () => {
    const nodes = [skill("html"), skill("css"), skill("react")];
    const edges = [edge("html", "css"), edge("css", "react")];
    const { nodes: placed } = await layoutGraph(nodes, edges);
    const x = Object.fromEntries(placed.map((node) => [node.id, node.x]));
    expect(x.html).toBeLessThan(x.css!);
    expect(x.css).toBeLessThan(x.react!);
  });

  it("returns every skill once, with its size", async () => {
    const { nodes } = await layoutGraph([skill("a", 1), skill("b")], []);
    expect(nodes.map((node) => node.id).sort()).toEqual(["a", "b"]);
    const a = nodes.find((node) => node.id === "a")!;
    expect({ width: a.width, height: a.height }).toEqual(nodeSize(1));
  });

  it("ignores links to unknown skills and self links", async () => {
    const { nodes } = await layoutGraph(
      [skill("a"), skill("b")],
      [edge("a", "ghost"), edge("b", "b"), edge("a", "b")],
    );
    expect(nodes).toHaveLength(2);
  });

  it("lays out nothing without skills", async () => {
    expect(await layoutGraph([], [])).toEqual({ nodes: [] });
  });
});

describe("nodeSize", () => {
  it("grows with demand", () => {
    expect(nodeSize(0).width).toBeLessThan(nodeSize(0.5).width);
    expect(nodeSize(0.5).width).toBeLessThan(nodeSize(1).width);
    expect(nodeSize(0.5).height).toBeLessThan(nodeSize(1).height);
  });

  it("bounds the demand between 0 and 1", () => {
    expect(nodeSize(7)).toEqual(nodeSize(1));
    expect(nodeSize(-3)).toEqual(nodeSize(0));
  });

  it("falls back to the default demand when it is unknown", () => {
    expect(nodeSize(null)).toEqual(nodeSize(DEFAULT_DEMAND));
    expect(nodeSize(Number.NaN)).toEqual(nodeSize(DEFAULT_DEMAND));
  });
});
