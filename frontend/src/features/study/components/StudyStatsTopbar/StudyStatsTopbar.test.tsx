import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StudyStatsTopbar } from "./StudyStatsTopbar";

describe("StudyStatsTopbar", () => {
  it("shows streak and week hours", () => {
    render(<StudyStatsTopbar stats={{ streakDays: 5, weekMinutes: 210 }} failed={false} />);
    expect(screen.getByText("Série : 5 jours")).toBeInTheDocument();
    expect(screen.getByText("Cette semaine : 3 h 30")).toBeInTheDocument();
  });

  it("stays silent while loading", () => {
    const { container } = render(<StudyStatsTopbar stats={null} failed={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says in one line that the figures are unavailable", () => {
    render(<StudyStatsTopbar stats={null} failed />);
    expect(screen.getByText("Rythme d'étude indisponible")).toBeInTheDocument();
  });
});
