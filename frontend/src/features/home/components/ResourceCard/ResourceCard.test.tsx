import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ResourceView } from "../viewTypes";
import { ResourceCard } from "./ResourceCard";

const RESOURCE: ResourceView = {
  title: "Optimiser une jointure",
  domain: "example.org",
  published: "2026-11-10",
  why: "Elle prolonge la leçon d'aujourd'hui.",
  url: "https://example.org/jointures",
};

describe("ResourceCard", () => {
  it("shows the title as an external link, the domain, the date and the reason", () => {
    render(<ResourceCard resource={RESOURCE} />);
    const link = screen.getByRole("link", {
      name: "Optimiser une jointure (s'ouvre dans un nouvel onglet)",
    });
    expect(link).toHaveAttribute("href", "https://example.org/jointures");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("example.org, 10 novembre 2026")).toBeInTheDocument();
    expect(
      screen.getByText("Pourquoi : Elle prolonge la leçon d'aujourd'hui."),
    ).toBeInTheDocument();
  });

  it("shows the domain alone when the page has no date", () => {
    render(<ResourceCard resource={{ ...RESOURCE, published: null }} />);
    expect(screen.getByText("example.org")).toBeInTheDocument();
  });

  it("says there is no resource this morning", () => {
    render(<ResourceCard resource={null} />);
    expect(screen.getByText("Pas de ressource ce matin.")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });
});
