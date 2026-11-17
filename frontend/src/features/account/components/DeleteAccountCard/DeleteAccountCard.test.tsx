import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DeleteAccountCard } from "./DeleteAccountCard";

const word = () => screen.getByLabelText("Tape SUPPRIMER pour confirmer");
const button = () => screen.getByRole("button", { name: "Tout supprimer" });

describe("DeleteAccountCard", () => {
  it("delete disabled until exact word", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <DeleteAccountCard pending={false} failure={null} onDelete={onDelete} onEdit={vi.fn()} />,
    );
    expect(button()).toBeDisabled();
    for (const typed of ["supprimer", "SUPPRIME", "SUPPRIMER ", " SUPPRIMER"]) {
      await user.clear(word());
      await user.type(word(), typed);
      expect(button()).toBeDisabled();
    }
    await user.clear(word());
    await user.type(word(), "SUPPRIMER");
    expect(button()).toBeEnabled();
    await user.click(button());
    expect(onDelete).toHaveBeenCalledWith("SUPPRIMER");
  });

  it("explains what goes and what stays", () => {
    render(
      <DeleteAccountCard pending={false} failure={null} onDelete={vi.fn()} onEdit={vi.fn()} />,
    );
    const card = screen.getByRole("region", { name: "Tout supprimer" });
    expect(card).toHaveTextContent("irréversible");
    expect(card).toHaveTextContent("fichier .env ne sont pas touchées");
  });

  it("links the warnings to the field, with the failure when there is one", () => {
    const { rerender } = render(
      <DeleteAccountCard pending={false} failure={null} onDelete={vi.fn()} onEdit={vi.fn()} />,
    );
    expect(word()).toHaveAccessibleDescription(/irréversible.*fichier .env ne sont pas touchées/);
    rerender(
      <DeleteAccountCard
        pending={false}
        failure={{ message: "La mémoire ne répond pas.", field: false }}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(word()).toHaveAccessibleDescription(/irréversible.*La mémoire ne répond pas./);
  });

  it("is busy and refuses a second click while the call runs", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<DeleteAccountCard pending failure={null} onDelete={onDelete} onEdit={vi.fn()} />);
    await user.type(word(), "SUPPRIMER");
    const busy = screen.getByRole("button", { name: "Suppression en cours…" });
    expect(busy).toHaveAttribute("aria-busy", "true");
    expect(busy).toHaveAttribute("aria-disabled", "true");
    await user.click(busy);
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("422 shows field error", () => {
    render(
      <DeleteAccountCard
        pending={false}
        failure={{ message: "Le mot de confirmation n'est pas bon.", field: true }}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(word()).toHaveAttribute("aria-invalid", "true");
    expect(word()).toHaveAccessibleDescription(/Le mot de confirmation n'est pas bon.$/);
  });

  it("focus moves to result message", () => {
    const { rerender } = render(
      <DeleteAccountCard pending={false} failure={null} onDelete={vi.fn()} onEdit={vi.fn()} />,
    );
    rerender(
      <DeleteAccountCard
        pending={false}
        failure={{ message: "La mémoire ne répond pas.", field: false }}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveFocus();
    expect(word()).not.toHaveAttribute("aria-invalid", "true");
  });
});
