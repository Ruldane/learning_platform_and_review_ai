import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { InterviewQuestionCard } from "./InterviewQuestionCard";

type Props = ComponentProps<typeof InterviewQuestionCard>;

function props(over: Partial<Props> = {}): Props {
  return {
    number: 2,
    total: 7,
    followUp: false,
    answered: false,
    disabled: false,
    stopLabel: "Terminer l'entretien",
    onAnswer: vi.fn(),
    onStop: vi.fn(),
    ...over,
  };
}

function setup(over: Partial<Props> = {}) {
  const given = props(over);
  const view = render(<InterviewQuestionCard {...given} />);
  const rerender = (next: Partial<Props>) =>
    view.rerender(<InterviewQuestionCard {...given} {...next} />);
  return { given, rerender, user: userEvent.setup() };
}

describe("InterviewQuestionCard", () => {
  it("names the question, puts the focus on the answer field and keeps the limit in sight", () => {
    setup();
    expect(screen.getByRole("region", { name: "Question 2 sur 7" })).toBeVisible();
    const field = screen.getByRole("textbox", { name: "Ta réponse écrite" });
    expect(field).toHaveFocus();
    expect(field).toHaveAttribute("maxlength", "4000");
    expect(screen.getByText(/4 000 caractères au plus/)).toBeVisible();
  });

  it("names a follow-up as such", () => {
    setup({ followUp: true });
    expect(screen.getByRole("region", { name: "Relance sur la question 2 sur 7" })).toBeVisible();
  });

  it("has a title even when the question number is not known yet", () => {
    setup({ number: null });
    expect(screen.getByRole("region", { name: "Question" })).toBeVisible();
  });

  it("sends the written answer", async () => {
    const { user, given } = setup();
    await user.type(screen.getByRole("textbox"), "Voici ma réponse");
    await user.click(screen.getByRole("button", { name: "Répondre" }));
    expect(given.onAnswer).toHaveBeenCalledWith("Voici ma réponse");
  });

  it("lets January end the interview with the server's own label", async () => {
    const { user, given } = setup({ stopLabel: "Arrêter ici" });
    await user.click(screen.getByRole("button", { name: "Arrêter ici" }));
    expect(given.onStop).toHaveBeenCalledTimes(1);
  });

  it("hides the stop button when the server offers no such option", () => {
    setup({ stopLabel: null });
    expect(screen.queryByRole("button", { name: /Terminer/ })).toBeNull();
  });

  it("locks the field and the buttons while an answer is on its way", () => {
    setup({ disabled: true });
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Terminer l'entretien" })).toBeDisabled();
  });

  it("folds once answered: « Réponse envoyée » and the answer, no field left", async () => {
    const { user, rerender } = setup();
    await user.type(screen.getByRole("textbox"), "Ma réponse");
    await user.click(screen.getByRole("button", { name: "Répondre" }));
    rerender({ answered: true, disabled: true });
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByText("Réponse envoyée")).toBeVisible();
    expect(screen.getByText("Ma réponse")).toBeVisible();
  });

  it("folds with « Tu as terminé l'entretien » after the stop button", async () => {
    const { user, rerender } = setup();
    await user.click(screen.getByRole("button", { name: "Terminer l'entretien" }));
    rerender({ answered: true, disabled: true });
    expect(screen.getByText("Tu as terminé l'entretien.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Terminer l'entretien" })).toBeNull();
  });
});
