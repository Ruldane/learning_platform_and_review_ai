import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RetryCard } from "./RetryCard";

const base = {
  help: "Le Conseil repart du début.",
  actionLabel: "Relancer le Conseil",
  busy: false,
  notice: null,
  error: null,
};

describe("RetryCard", () => {
  it("relaunches on click and says what it does", async () => {
    const onRetry = vi.fn();
    render(<RetryCard {...base} title="Échec." onRetry={onRetry} />);
    const button = screen.getByRole("button", { name: "Relancer le Conseil" });
    expect(button).toHaveAccessibleDescription("Le Conseil repart du début.");
    expect(screen.getByText("Échec.")).toBeInTheDocument();
    await userEvent.setup().click(button);
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("is disabled while busy, and shows a notice apart from an error", () => {
    render(
      <RetryCard {...base} busy notice="Relu." error="Panne." onRetry={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Relance en cours…" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Relu.");
    expect(screen.getByRole("alert")).toHaveTextContent("Panne.");
  });
});
