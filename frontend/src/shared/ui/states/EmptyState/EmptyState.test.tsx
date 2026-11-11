import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("affiche le titre et la description", () => {
    render(<EmptyState title="Rien ici" description="Reviens plus tard." />);
    expect(screen.getByRole("heading", { name: "Rien ici" })).toBeInTheDocument();
    expect(screen.getByText("Reviens plus tard.")).toBeInTheDocument();
  });

  it("n'affiche pas de bouton sans action", () => {
    render(<EmptyState title="Rien ici" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("appelle l'action au clic", async () => {
    const onClick = vi.fn();
    render(<EmptyState title="Rien ici" action={{ label: "Ajouter", onClick }} />);
    await userEvent.click(screen.getByRole("button", { name: "Ajouter" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
