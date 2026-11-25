import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CoverageGauge } from "./CoverageGauge";

describe("CoverageGauge", () => {
  it("writes the change from before to after", () => {
    render(<CoverageGauge before={58} after={83} />);
    expect(screen.getByText("Requirement coverage: 58% → 83%")).toBeInTheDocument();
    const meter = screen.getByRole("meter", { name: "Requirement coverage: 58% → 83%" });
    expect(meter).toHaveAttribute("aria-valuenow", "83");
  });

  it("shows only the starting value while there is no generated CV", () => {
    render(<CoverageGauge before={58} after={null} />);
    expect(screen.getByText("Requirement coverage: 58%")).toBeInTheDocument();
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "58");
  });

  it("keeps the values between 0 and 100", () => {
    render(<CoverageGauge before={-4} after={140.4} />);
    expect(screen.getByText("Requirement coverage: 0% → 100%")).toBeInTheDocument();
  });

  it("explains what is measured", () => {
    render(<CoverageGauge before={10} after={null} />);
    expect(screen.getByText(/posting's required skills/)).toBeInTheDocument();
  });
});
