import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RadarAlerts } from "./RadarAlerts";

describe("RadarAlerts", () => {
  it("shows each alert with its skill and the server's message", () => {
    render(
      <RadarAlerts
        alerts={[
          {
            skill: "Kubernetes",
            share: 0.62,
            message: "Demandée dans 62 % des offres, absente de ton programme.",
          },
        ]}
      />,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Alerts" })).toBeVisible();
    const list = screen.getByRole("list", { name: "Scan alerts" });
    expect(list).toHaveTextContent(
      "Kubernetes : Demandée dans 62 % des offres, absente de ton programme.",
    );
  });

  it("hides the warning icon from assistive technology", () => {
    const { container } = render(
      <RadarAlerts alerts={[{ skill: "dbt", share: 0.5, message: "Absente." }]} />,
    );
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("says there is no alert", () => {
    render(<RadarAlerts alerts={[]} />);
    expect(screen.getByText("No alerts for this scan.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });
});
