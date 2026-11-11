import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoadingState } from "./LoadingState";

describe("LoadingState", () => {
  it("annonce le chargement par défaut", () => {
    render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Chargement…");
  });

  it("accepte un libellé personnalisé", () => {
    render(<LoadingState label="Analyse en cours…" />);
    expect(screen.getByRole("status")).toHaveTextContent("Analyse en cours…");
  });
});
