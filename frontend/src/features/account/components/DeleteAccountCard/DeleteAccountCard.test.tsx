import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DeleteAccountCard } from "./DeleteAccountCard";

const word = () => screen.getByLabelText("Type SUPPRIMER to confirm");
const button = () => screen.getByRole("button", { name: "Delete everything" });

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
    const card = screen.getByRole("region", { name: "Delete everything" });
    expect(card).toHaveTextContent("This cannot be undone.");
    expect(card).toHaveTextContent("API keys written in the .env file are not affected.");
  });

  it("links the warnings to the field, with the failure when there is one", () => {
    const { rerender } = render(
      <DeleteAccountCard pending={false} failure={null} onDelete={vi.fn()} onEdit={vi.fn()} />,
    );
    expect(word()).toHaveAccessibleDescription(
      /This cannot be undone.*API keys written in the \.env file are not affected/,
    );
    rerender(
      <DeleteAccountCard
        pending={false}
        failure={{ message: "The vector memory isn't responding.", field: false }}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(word()).toHaveAccessibleDescription(/This cannot be undone.*memory isn't responding/);
  });

  it("is busy and refuses a second click while the call runs", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<DeleteAccountCard pending failure={null} onDelete={onDelete} onEdit={vi.fn()} />);
    await user.type(word(), "SUPPRIMER");
    const busy = screen.getByRole("button", { name: "Deleting…" });
    expect(busy).toHaveAttribute("aria-busy", "true");
    expect(busy).toHaveAttribute("aria-disabled", "true");
    await user.click(busy);
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("422 shows field error", () => {
    render(
      <DeleteAccountCard
        pending={false}
        failure={{ message: "The confirmation word is wrong.", field: true }}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(word()).toHaveAttribute("aria-invalid", "true");
    expect(word()).toHaveAccessibleDescription(/The confirmation word is wrong\.$/);
  });

  it("focus moves to result message", () => {
    const { rerender } = render(
      <DeleteAccountCard pending={false} failure={null} onDelete={vi.fn()} onEdit={vi.fn()} />,
    );
    rerender(
      <DeleteAccountCard
        pending={false}
        failure={{ message: "The vector memory isn't responding.", field: false }}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("delete-failure")).toHaveFocus();
    // Lu une fois : le focus le porte, il n'est pas aussi une alerte.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(word()).not.toHaveAttribute("aria-invalid", "true");
  });
});
