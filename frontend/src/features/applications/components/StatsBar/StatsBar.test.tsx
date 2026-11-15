import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeStats } from "../fixtures";
import { StatsBar } from "./StatsBar";

describe("StatsBar", () => {
  it("shows the count of each of the eight statuses, zero included", () => {
    render(<StatsBar stats={makeStats()} />);
    const list = screen.getByRole("list", { name: "Par statut" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "À postuler0",
      "Postulée3",
      "Relancée0",
      "Entretien1",
      "Offre0",
      "Refus1",
      "Sans réponse0",
      "Retirée0",
    ]);
  });

  it("shows the response rate as a percentage, the mean delay and the due reminders", () => {
    render(<StatsBar stats={makeStats()} />);
    expect(screen.getByText("Taux de réponse").nextSibling).toHaveTextContent("40 %");
    expect(screen.getByText("Délai moyen de réponse").nextSibling).toHaveTextContent("6,5 jours");
    expect(screen.getByText("Relances dues").nextSibling).toHaveTextContent("2");
  });

  it("shows a dash when there is no application sent to answer", () => {
    render(<StatsBar stats={makeStats({ responseRate: null, meanResponseDays: null })} />);
    expect(screen.getByText("Taux de réponse").nextSibling).toHaveTextContent("—");
    expect(screen.getByText("Délai moyen de réponse").nextSibling).toHaveTextContent("—");
  });

  it("keeps a real zero rate as 0 %, distinct from no data", () => {
    render(<StatsBar stats={makeStats({ responseRate: 0, meanResponseDays: 0 })} />);
    expect(screen.getByText("Taux de réponse").nextSibling).toHaveTextContent("0 %");
    expect(screen.getByText("Délai moyen de réponse").nextSibling).toHaveTextContent("0 jour");
  });

  it("uses the singular for one day", () => {
    render(<StatsBar stats={makeStats({ meanResponseDays: 1 })} />);
    expect(screen.getByText("Délai moyen de réponse").nextSibling).toHaveTextContent("1 jour");
  });

  it("is a named region", () => {
    render(<StatsBar stats={makeStats()} />);
    expect(
      screen.getByRole("region", { name: "Indicateurs des candidatures" }),
    ).toBeInTheDocument();
  });
});
