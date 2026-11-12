import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeWeek } from "../fixtures";
import { WeekHeader } from "./WeekHeader";

describe("WeekHeader", () => {
  it("shows the theme, objective and deliverable", () => {
    render(<WeekHeader week={makeWeek()} />);
    expect(
      screen.getByRole("heading", { name: "Semaine 1 : Premiers pas en Python" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Écrire un script de 50 lignes sans aide.")).toBeInTheDocument();
    expect(screen.getByText("Un script qui trie un fichier CSV.")).toBeInTheDocument();
  });

  it("shows the load against 85 %", () => {
    render(<WeekHeader week={makeWeek()} />);
    expect(screen.getByText(/11 h 54/)).toBeInTheDocument();
    expect(screen.getByText("11 h 30 / 11 h 54 (85 %)")).toBeInTheDocument();
    expect(screen.getByText("Dans le plafond de la semaine.")).toBeInTheDocument();
  });

  it("says in text when the load passes the cap", () => {
    render(<WeekHeader week={makeWeek({ loadMinutes: 800 })} />);
    expect(screen.getByText("Au-delà du plafond de la semaine.")).toBeInTheDocument();
  });
});
