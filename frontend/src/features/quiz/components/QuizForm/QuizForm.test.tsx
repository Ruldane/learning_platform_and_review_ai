import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { QuestionView } from "../viewTypes";
import { QuizForm } from "./QuizForm";

const CODE = 'const a = "<script>alert(1)</script>";\nconsole.log(a);';

const QUESTIONS: QuestionView[] = [
  {
    id: "q1",
    rank: 1,
    type: "qcm",
    prompt: "Quel index accélère une recherche par égalité ?",
    code: null,
    choices: ["Hash", "Aucun", "Bitmap"],
  },
  { id: "q2", rank: 2, type: "short", prompt: "Que fait EXPLAIN ?", code: null, choices: [] },
  { id: "q3", rank: 3, type: "code", prompt: "Que affiche ce code ?", code: CODE, choices: [] },
  {
    id: "q4",
    rank: 4,
    type: "explain",
    prompt: "Explique ce qu'est une jointure.",
    code: null,
    choices: [],
  },
];

function setup(props: Partial<Parameters<typeof QuizForm>[0]> = {}) {
  const onSubmit = vi.fn();
  render(<QuizForm questions={QUESTIONS} disabled={false} onSubmit={onSubmit} {...props} />);
  return { onSubmit };
}

const field = (rank: number) =>
  screen.getByRole("textbox", { name: `Ta réponse à la question ${rank}` });

async function answerAll() {
  await userEvent.click(screen.getByRole("radio", { name: "Bitmap" }));
  await userEvent.type(field(2), " Plan ");
  await userEvent.type(field(3), "Le texte");
  await userEvent.type(field(4), "Un lien");
}

afterEach(() => vi.restoreAllMocks());

describe("QuizForm", () => {
  it("renders the four question types", () => {
    setup();
    const group = screen.getByRole("radiogroup", {
      name: /Quel index accélère une recherche par égalité/,
    });
    expect(within(group).getAllByRole("radio")).toHaveLength(3);
    expect(screen.getByText("QCM")).toBeInTheDocument();
    expect(screen.getByText("Réponse courte")).toBeInTheDocument();
    expect(screen.getByText("Lecture de code")).toBeInTheDocument();
    expect(screen.getByText("Explique avec tes mots")).toBeInTheDocument();
    expect(screen.getAllByRole("textbox")).toHaveLength(3);
  });

  it("shows code as inert text in a pre block", () => {
    setup();
    const pre = screen.getByLabelText("Code de la question 3");
    expect(pre.tagName).toBe("PRE");
    expect(pre.textContent).toBe(CODE);
    expect(pre.querySelector("script")).toBeNull();
  });

  it("lists questions by rank", () => {
    setup({ questions: [...QUESTIONS].reverse() });
    const ids = screen
      .getAllByRole("listitem")
      .map((li) => li.dataset.question)
      .filter(Boolean);
    expect(ids).toEqual(["q1", "q2", "q3", "q4"]);
  });

  it("sends every answer in rank order when all are filled", async () => {
    const { onSubmit } = setup();
    await answerAll();
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith([
      { question_id: "q1", choice: 2, text: "" },
      { question_id: "q2", choice: null, text: "Plan" },
      { question_id: "q3", choice: null, text: "Le texte" },
      { question_id: "q4", choice: null, text: "Un lien" },
    ]);
  });

  it("asks inline before sending empty answers", async () => {
    const confirm = vi.spyOn(window, "confirm");
    const { onSubmit } = setup();
    await userEvent.click(screen.getByRole("radio", { name: "Hash" }));
    await userEvent.type(field(2), "x");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(confirm).not.toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
    const ask = screen.getByRole("alert");
    expect(ask).toHaveTextContent("2 questions sans réponse (3, 4)");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer quand même" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith([
      { question_id: "q1", choice: 0, text: "" },
      { question_id: "q2", choice: null, text: "x" },
      { question_id: "q3", choice: null, text: "" },
      { question_id: "q4", choice: null, text: "" },
    ]);
  });

  it("goes back to the quiz instead of sending", async () => {
    const { onSubmit } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(screen.getByRole("alert")).toHaveTextContent("4 questions sans réponse");
    await userEvent.click(screen.getByRole("button", { name: "Continuer le quiz" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Envoyer" })).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("says one question is left in the singular", async () => {
    setup();
    await userEvent.click(screen.getByRole("radio", { name: "Hash" }));
    await userEvent.type(field(2), "x");
    await userEvent.type(field(3), "x");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(screen.getByRole("alert")).toHaveTextContent("1 question sans réponse (4)");
  });

  it("counts a blank text as empty", async () => {
    setup();
    await userEvent.type(field(2), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(screen.getByRole("alert")).toHaveTextContent("4 questions sans réponse");
  });

  it("disables every field and the button while sending", () => {
    setup({ disabled: true });
    for (const control of [...screen.getAllByRole("radio"), ...screen.getAllByRole("textbox")]) {
      expect(control).toBeDisabled();
    }
    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
  });

  it("limits open answers to 4000 characters", () => {
    setup();
    expect(field(2)).toHaveAttribute("maxlength", "4000");
  });

  it("counts the answers given", async () => {
    setup();
    expect(screen.getByText("Répondu : 0 sur 4")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Hash" }));
    expect(screen.getByText("Répondu : 1 sur 4")).toBeInTheDocument();
  });
});
