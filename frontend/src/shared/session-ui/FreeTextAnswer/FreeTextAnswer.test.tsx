import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FreeTextAnswer } from "./FreeTextAnswer";

describe("FreeTextAnswer", () => {
  it("focuses the field and submits the trimmed text on Enter", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<FreeTextAnswer disabled={false} onSubmit={onSubmit} />);
    expect(screen.getByRole("textbox", { name: "Ta réponse" })).toHaveFocus();
    await user.keyboard("  Pense aux débutants {Enter}");
    expect(onSubmit).toHaveBeenCalledWith("Pense aux débutants");
  });

  it("refuses an empty answer", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<FreeTextAnswer disabled={false} onSubmit={onSubmit} />);
    await user.keyboard("   {Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Répondre" })).toBeDisabled();
  });

  it("is locked when disabled", () => {
    render(<FreeTextAnswer disabled onSubmit={vi.fn()} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
