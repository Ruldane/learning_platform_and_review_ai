import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AdviceCard } from "./AdviceCard";

describe("AdviceCard", () => {
  it("shows the council's two sentences under « Le conseil »", () => {
    render(
      <AdviceCard
        status="ready"
        sentences={["Révise tes fiches avant de lire.", "Une jointure par jour suffit."]}
      />,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Le conseil" })).toBeVisible();
    expect(screen.getByText("Révise tes fiches avant de lire.")).toBeInTheDocument();
    expect(screen.getByText("Une jointure par jour suffit.")).toBeInTheDocument();
  });

  it("says the council is meeting while the advice is pending", () => {
    render(<AdviceCard status="pending" sentences={null} />);
    expect(screen.getByText("Le conseil se réunit…")).toBeInTheDocument();
  });

  it("announces the advice when it arrives, in a polite live region that is always there", () => {
    const { rerender } = render(<AdviceCard status="pending" sentences={null} />);
    const region = screen.getByText("Le conseil se réunit…").parentElement;
    expect(region).toHaveAttribute("aria-live", "polite");
    rerender(<AdviceCard status="ready" sentences={["Révise tes fiches avant de lire."]} />);
    expect(screen.getByText("Révise tes fiches avant de lire.").parentElement).toBe(region);
  });

  it.each(["failed", "unavailable"] as const)(
    "says the council could not speak when the status is %s, without any retry",
    (status) => {
      render(<AdviceCard status={status} sentences={null} />);
      expect(screen.getByText("Le conseil n'a rien pu dire ce matin.")).toBeInTheDocument();
      expect(screen.queryByRole("button")).toBeNull();
      expect(screen.queryByText(/clé/i)).toBeNull();
    },
  );

  it("never shows an empty advice marked ready as if it had spoken", () => {
    render(<AdviceCard status="ready" sentences={[]} />);
    expect(screen.getByText("Le conseil n'a rien pu dire ce matin.")).toBeInTheDocument();
  });
});
