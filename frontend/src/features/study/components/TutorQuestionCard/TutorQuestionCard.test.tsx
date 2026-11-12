import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { TutorOptionView } from "../viewTypes";
import { TutorQuestionCard } from "./TutorQuestionCard";

const QUESTION = "Pourquoi un index accélère-t-il une recherche ?";
const STUCK: TutorOptionView = { value: "stuck", label: "Je bloque (1/3)" };
const SKIP: TutorOptionView = { value: "skip", label: "Passer" };

function setup(props: Partial<Parameters<typeof TutorQuestionCard>[0]> = {}) {
  const handlers = { onAnswer: vi.fn(), onStuck: vi.fn(), onSkip: vi.fn() };
  const all = {
    question: QUESTION,
    options: [STUCK, SKIP],
    answered: false,
    disabled: false,
    ...handlers,
    ...props,
  };
  const view = render(<TutorQuestionCard {...all} />);
  return { ...handlers, all, ...view };
}

describe("TutorQuestionCard", () => {
  it("shows the question, an answer field and the options", () => {
    setup();
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Ta réponse" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Je bloque (1/3)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Passer" })).toBeInTheDocument();
  });

  it("reads the hint count from the option label instead of counting", () => {
    setup({ options: [{ value: "stuck", label: "Je bloque (2/3)" }, SKIP] });
    expect(screen.getByRole("button", { name: "Je bloque (2/3)" })).toBeInTheDocument();
  });

  it("shows solution button after three hints", () => {
    setup({ options: [{ value: "stuck", label: "Voir la solution" }, SKIP] });
    expect(screen.getByRole("button", { name: "Voir la solution" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Je bloque/ })).not.toBeInTheDocument();
  });

  it("asks for a hint or the solution with the same option, and can skip", async () => {
    const { onStuck, onSkip } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Je bloque (1/3)" }));
    expect(onStuck).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole("button", { name: "Passer" }));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it("falls back to plain labels when the interruption gives none", () => {
    setup({ options: [] });
    expect(screen.getByRole("button", { name: "Je bloque" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Passer" })).toBeInTheDocument();
  });

  it("sends the trimmed answer", async () => {
    const { onAnswer } = setup();
    await userEvent.type(
      screen.getByRole("textbox", { name: "Ta réponse" }),
      "  Il évite un parcours complet  ",
    );
    await userEvent.click(screen.getByRole("button", { name: "Répondre" }));
    expect(onAnswer).toHaveBeenCalledWith("Il évite un parcours complet");
  });

  it("sends with Ctrl+Enter", async () => {
    const { onAnswer } = setup();
    await userEvent.type(screen.getByRole("textbox", { name: "Ta réponse" }), "Un arbre trié");
    await userEvent.keyboard("{Control>}{Enter}{/Control}");
    expect(onAnswer).toHaveBeenCalledWith("Un arbre trié");
  });

  it("refuses an empty answer", async () => {
    const { onAnswer } = setup();
    expect(screen.getByRole("button", { name: "Répondre" })).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: "Ta réponse" }), "   ");
    expect(screen.getByRole("button", { name: "Répondre" })).toBeDisabled();
    expect(onAnswer).not.toHaveBeenCalled();
  });

  it("limits the answer to 4000 characters", () => {
    setup();
    expect(screen.getByRole("textbox", { name: "Ta réponse" })).toHaveAttribute(
      "maxlength",
      "4000",
    );
  });

  it("disables everything while an answer is on its way", () => {
    setup({ disabled: true });
    expect(screen.getByRole("textbox", { name: "Ta réponse" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Je bloque (1/3)" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Passer" })).toBeDisabled();
  });

  it("collapses once answered", () => {
    setup({ answered: true });
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps the answer typed here, read-only, once answered", async () => {
    const { rerender, all } = setup();
    await userEvent.type(screen.getByRole("textbox", { name: "Ta réponse" }), "Un arbre trié");
    await userEvent.click(screen.getByRole("button", { name: "Répondre" }));
    rerender(<TutorQuestionCard {...all} answered />);
    expect(screen.getByText("Un arbre trié")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("shows only the question and the receipt after a reload", () => {
    setup({ answered: true });
    expect(screen.queryByText("Ta réponse")).not.toBeInTheDocument();
  });
});
