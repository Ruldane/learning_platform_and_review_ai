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

describe("FreeTextAnswer, long answer", () => {
  it("writes in a text area where Enter adds a line and Ctrl+Enter sends", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<FreeTextAnswer disabled={false} multiline onSubmit={onSubmit} />);
    const field = screen.getByRole("textbox", { name: "Ta réponse" });
    expect(field.tagName).toBe("TEXTAREA");
    await user.type(field, "Première ligne{Enter}Seconde ligne");
    expect(onSubmit).not.toHaveBeenCalled();
    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(onSubmit).toHaveBeenCalledWith("Première ligne\nSeconde ligne");
  });

  it("limits the length, takes its own label and names the limit", () => {
    render(
      <FreeTextAnswer
        disabled={false}
        multiline
        maxLength={50}
        label="Ta réponse écrite"
        onSubmit={vi.fn()}
      />,
    );
    const field = screen.getByRole("textbox", { name: "Ta réponse écrite" });
    expect(field).toHaveAttribute("maxlength", "50");
  });
});
