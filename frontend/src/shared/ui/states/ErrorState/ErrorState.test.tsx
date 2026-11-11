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
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
