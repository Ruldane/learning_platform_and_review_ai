import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeWeek } from "../fixtures";
import { WeekHeader } from "./WeekHeader";

describe("WeekHeader", () => {
  it("shows the theme, objective and deliverable", () => {
    render(<WeekHeader week={makeWeek()} />);
    expect(
      screen.getByRole("heading", { name: "Week 1: Premiers pas en Python" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Écrire un script de 50 lignes sans aide.")).toBeInTheDocument();
    expect(screen.getByText("Un script qui trie un fichier CSV.")).toBeInTheDocument();
  });

  it("shows the stage and the reason of the week when the program gives them", () => {
    render(
      <WeekHeader
        week={makeWeek({
          stage: "practice",
          rationale: "Les outils viennent après les messages.",
        })}
      />,
    );
    expect(screen.getByText("Stage")).toBeInTheDocument();
    expect(screen.getByText("Everyday practice")).toBeInTheDocument();
    expect(
      screen.getByText("Why now: Les outils viennent après les messages."),
    ).toBeInTheDocument();
  });

  it.each([
    ["foundations", "Foundations"],
    ["advanced", "Advanced"],
  ] as const)("names the %s stage", (stage, label) => {
    render(<WeekHeader week={makeWeek({ stage })} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows neither stage nor reason when the program has none", () => {
    render(<WeekHeader week={makeWeek()} />);
    expect(screen.queryByText("Stage")).not.toBeInTheDocument();
    expect(screen.queryByText(/^Why now:/)).not.toBeInTheDocument();
  });

  it("shows the load against 85%", () => {
    render(<WeekHeader week={makeWeek()} />);
    expect(screen.getByText(/11 h 54/)).toBeInTheDocument();
    expect(screen.getByText("11 h 30 / 11 h 54 (85%)")).toBeInTheDocument();
    expect(screen.getByText("Within the week’s cap.")).toBeInTheDocument();
  });

  it("says in text when the load passes the cap", () => {
    render(<WeekHeader week={makeWeek({ loadMinutes: 800 })} />);
    expect(screen.getByText("Over the week’s cap.")).toBeInTheDocument();
  });
});
