import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InterruptCard } from "./InterruptCard";

const withOptions = {
  interrupt_id: "i1",
  kind: "choice",
  question: "Quelle suite donner ?",
  options: [
    { label: "Plus concret", value: "concret" },
    { label: "Plus court", value: "court" },
  ],
};
const freeText = { ...withOptions, options: [] };

describe("InterruptCard", () => {
  it("calls onAnswer with the option value", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={withOptions} answered={false} onAnswer={onAnswer} />);
    expect(screen.getByText("Quelle suite donner ?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Plus concret" }));
    expect(onAnswer).toHaveBeenCalledWith("concret");
  });

  it("can be answered with the keyboard alone", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={withOptions} answered={false} onAnswer={onAnswer} />);
    expect(screen.getByRole("button", { name: "Plus concret" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Plus court" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onAnswer).toHaveBeenCalledWith("court");
  });

  it("shows a free text field when there are no options", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={freeText} answered={false} onAnswer={onAnswer} />);
    const field = screen.getByRole("textbox", { name: "Ta réponse" });
    expect(field).toHaveFocus();
    await user.type(field, "Pense aux débutants{Enter}");
    expect(onAnswer).toHaveBeenCalledWith("Pense aux débutants");
  });

  it("does not send an empty free text answer", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={freeText} answered={false} onAnswer={onAnswer} />);
    await user.type(screen.getByRole("textbox"), "  {Enter}");
    expect(onAnswer).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Répondre" })).toBeDisabled();
  });

  it("locks the card once answered and does not steal focus", () => {
    render(<InterruptCard interrupt={withOptions} answered onAnswer={vi.fn()} />);
    const option = screen.getByRole("button", { name: "Plus concret" });
    expect(option).toBeDisabled();
    expect(option).not.toHaveFocus();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
  });

  it("disables the options while an answer is being sent", () => {
    render(<InterruptCard interrupt={withOptions} answered={false} disabled onAnswer={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Plus court" })).toBeDisabled();
  });

  it("never opens a blocking browser dialog", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm");
    render(<InterruptCard interrupt={withOptions} answered={false} onAnswer={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Plus court" }));
    expect(confirm).not.toHaveBeenCalled();
    confirm.mockRestore();
  });
});
