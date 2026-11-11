import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("affiche l'accueil en français avec un lien d'évitement", () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Bienvenue sur Tremplin" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Aller au contenu" })).toHaveAttribute(
      "href",
      "#contenu",
    );
  });

  it("affiche la page introuvable pour une route inconnue", () => {
    window.history.pushState({}, "", "/nimporte-quoi");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retour à l'accueil" })).toBeInTheDocument();
  });
});
