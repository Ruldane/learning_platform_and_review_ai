import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TeacherAsk } from "./TeacherAsk";

const setup = (over: Partial<Parameters<typeof TeacherAsk>[0]> = {}) => {
  const calls = { onHint: vi.fn(), onWhy: vi.fn(), onQuestion: vi.fn() };
  render(<TeacherAsk busy={false} canExplain {...calls} {...over} />);
  return { ...calls, user: userEvent.setup() };
};

describe("TeacherAsk", () => {
  it("asks for a hint, for the reason of an error, or a question", async () => {
    const { user, onHint, onWhy, onQuestion } = setup();
    await user.click(screen.getByRole("button", { name: "Indice" }));
    await user.click(screen.getByRole("button", { name: "Pourquoi cette erreur ?" }));
    await user.type(
      screen.getByRole("textbox", { name: "Ta question" }),
      "  C'est quoi un tuple ? ",
    );
    await user.click(screen.getByRole("button", { name: "Poser la question" }));
    expect(onHint).toHaveBeenCalledTimes(1);
    expect(onWhy).toHaveBeenCalledTimes(1);
    expect(onQuestion).toHaveBeenCalledWith("C'est quoi un tuple ?");
    expect(screen.getByRole("textbox", { name: "Ta question" })).toHaveValue("");
  });

  it("never sends an empty question", async () => {
    const { user, onQuestion } = setup();
    expect(screen.getByRole("button", { name: "Poser la question" })).toBeDisabled();
    await user.type(screen.getByRole("textbox", { name: "Ta question" }), "   ");
    expect(screen.getByRole("button", { name: "Poser la question" })).toBeDisabled();
    expect(onQuestion).not.toHaveBeenCalled();
  });

  it("has nothing to explain before an error, and waits while the teacher works", () => {
    setup({ canExplain: false });
    expect(screen.getByRole("button", { name: "Pourquoi cette erreur ?" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Indice" })).toBeEnabled();
  });

  it("ignores every button while the teacher is working, and keeps them focusable", async () => {
    const { user, onHint, onWhy } = setup({ busy: true });
    await user.click(screen.getByRole("button", { name: "Indice" }));
    await user.click(screen.getByRole("button", { name: "Pourquoi cette erreur ?" }));
    expect(onHint).not.toHaveBeenCalled();
    expect(onWhy).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Indice" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("button", { name: "Indice" })).toBeEnabled();
  });
});
