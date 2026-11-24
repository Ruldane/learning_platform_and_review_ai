import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("affiche le message dans une alerte", () => {
    render(<ErrorState message="Panne du serveur." onRetry={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Panne du serveur.");
  });

  it("appelle onRetry au clic sur Réessayer", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Panne du serveur." onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("remplace « Réessayer » par l'action donnée", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Introuvable." onRetry={onRetry} actionLabel="New debate" />);
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "New debate" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
