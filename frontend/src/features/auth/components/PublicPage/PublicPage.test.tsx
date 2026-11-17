import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PublicPage } from "./PublicPage";

describe("PublicPage", () => {
  it("is a page of its own whose title takes the focus", () => {
    render(
      <PublicPage title="Connexion">
        <p>Corps</p>
      </PublicPage>,
    );
    expect(screen.getByRole("main")).toContainElement(screen.getByText("Corps"));
    expect(screen.getByRole("heading", { level: 1, name: "Connexion" })).toHaveFocus();
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("takes the focus only once the page has settled (a retry error is gone)", () => {
    const { rerender } = render(
      <PublicPage title="Connexion" settled={false}>
        <button type="button">Réessayer</button>
      </PublicPage>,
    );
    expect(screen.getByRole("heading", { name: "Connexion" })).not.toHaveFocus();
    rerender(
      <PublicPage title="Connexion" settled>
        <p>Carte</p>
      </PublicPage>,
    );
    expect(screen.getByRole("heading", { name: "Connexion" })).toHaveFocus();
  });
});
