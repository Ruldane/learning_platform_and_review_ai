import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ZoneView } from "../viewTypes";
import { TemplateCompare } from "./TemplateCompare";
import { zoneSentences } from "./zoneSentences";

const ZONES: ZoneView[] = [
  { zone: "gauche", original: 0.4, render: 0.22 },
  { zone: "haut", original: 0.3, render: 0.31 },
  { zone: "bas", original: 0.1, render: 0.2 },
];

function setup(props: Partial<Parameters<typeof TemplateCompare>[0]> = {}) {
  render(
    <TemplateCompare
      originalPages={["/o1.png", "/o2.png"]}
      renderPages={["/r1.png", "/r2.png"]}
      score={87}
      zones={ZONES}
      passes={2}
      {...props}
    />,
  );
}

describe("TemplateCompare", () => {
  it("shows the two columns, page by page, with their alternative texts", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Ton CV" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Modèle recréé" })).toBeInTheDocument();
    const page2 = screen.getByRole("region", { name: "Page 2" });
    expect(within(page2).getByRole("img", { name: "Page 2 de ton CV d'origine" })).toHaveAttribute(
      "src",
      "/o2.png",
    );
    expect(within(page2).getByRole("img", { name: "Page 2 du modèle recréé" })).toHaveAttribute(
      "src",
      "/r2.png",
    );
    expect(screen.getAllByRole("img")).toHaveLength(4);
  });

  it("shows the score, the passes and the zones as sentences", () => {
    setup();
    expect(screen.getByText("Ressemblance : 87 %")).toBeInTheDocument();
    expect(screen.getByText("Après 2 ajustements.")).toBeInTheDocument();
    const items = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(items).toEqual([
      "Le modèle recréé a 18 % d'encre en moins à gauche que ton CV.",
      "Le modèle recréé a 10 % d'encre en plus en bas que ton CV.",
    ]);
  });

  it("says when the score is not computed, and when no zone differs", () => {
    setup({ score: null, zones: [] });
    expect(screen.getByText("Ressemblance : pas encore calculée")).toBeInTheDocument();
    expect(screen.queryByText("Où le modèle recréé diffère")).not.toBeInTheDocument();
  });

  it("says when no zone stands out", () => {
    setup({ zones: [{ zone: "haut", original: 0.3, render: 0.31 }], passes: 0 });
    expect(screen.getByText("Aucun écart notable de mise en page.")).toBeInTheDocument();
    expect(screen.getByText("Sans ajustement.")).toBeInTheDocument();
  });

  it("says when a page is missing on one side", () => {
    setup({ renderPages: ["/r1.png"] });
    expect(screen.getByText("Pas de page 2 de ce côté.")).toBeInTheDocument();
  });

  it("switches to the overlay with a keyboard-operable slider", async () => {
    setup();
    const overlay = screen.getByRole("button", { name: "Superposition" });
    expect(screen.getByRole("button", { name: "Côte à côte" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(overlay);
    expect(overlay).toHaveAttribute("aria-pressed", "true");
    const slider = screen.getByRole("slider", { name: "Curseur de comparaison" });
    expect(slider).toHaveAttribute("aria-valuetext", "Ton CV jusqu'à 50 % de la largeur");
    // Un curseur natif (`input type="range"`) se règle aux flèches : il suffit qu'il prenne le focus.
    await userEvent.tab();
    expect(slider).toHaveFocus();
    fireEvent.change(slider, { target: { value: "20" } });
    expect(slider).toHaveAttribute("aria-valuetext", "Ton CV jusqu'à 20 % de la largeur");
    expect(screen.getByRole("img", { name: "Page 1 de ton CV d'origine" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Page 1 du modèle recréé" })).toBeInTheDocument();
  });

  it("says when there is nothing to compare", () => {
    setup({ originalPages: [], renderPages: [] });
    expect(screen.getByText("Aucune page à comparer pour l'instant.")).toBeInTheDocument();
  });
});

describe("zoneSentences", () => {
  it("keeps the four biggest gaps over five points", () => {
    const zones: ZoneView[] = [
      { zone: "haut", original: 0.1, render: 0.2 },
      { zone: "milieu", original: 0.1, render: 0.3 },
      { zone: "bas", original: 0.5, render: 0.2 },
      { zone: "gauche", original: 0.1, render: 0.17 },
      { zone: "droite", original: 0.1, render: 0.15 },
    ];
    expect(zoneSentences(zones)).toHaveLength(4);
    expect(zoneSentences(zones)[0]).toBe(
      "Le modèle recréé a 30 % d'encre en moins en bas que ton CV.",
    );
  });
});
