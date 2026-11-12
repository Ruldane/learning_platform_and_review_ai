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

const framing = {
  interrupt_id: "i2",
  kind: "framing",
  question: "Réponds aux questions de cadrage.",
  options: [{ label: "Lancer la recherche", value: "go" }],
  fields: [
    { id: "q1", label: "Quel type d'entreprise vises-tu ?", max_length: 2000, required: false },
    { id: "q2", label: "Quand veux-tu changer de poste ?", max_length: 2000, required: false },
  ],
};

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

  it("folds into the question and a receipt once answered", () => {
    render(<InterruptCard interrupt={withOptions} answered onAnswer={vi.fn()} />);
    expect(screen.getByText("Quelle suite donner ?")).toBeInTheDocument();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("shows no free text field once answered", () => {
    render(<InterruptCard interrupt={freeText} answered onAnswer={vi.fn()} />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
  });

  it("disables the options while an answer is being sent", () => {
    render(<InterruptCard interrupt={withOptions} answered={false} disabled onAnswer={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Plus court" })).toBeDisabled();
  });

  it("with fields sends answers", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={framing} answered={false} onAnswer={onAnswer} />);
    await user.type(
      screen.getByRole("textbox", { name: "Quel type d'entreprise vises-tu ?" }),
      "Startup",
    );
    await user.click(screen.getByRole("button", { name: "Répondre" }));
    expect(onAnswer).toHaveBeenCalledWith({ answers: { q1: "Startup" } });
  });

  it("omits blank answers and trims the others", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={framing} answered={false} onAnswer={onAnswer} />);
    await user.type(screen.getByLabelText("Quel type d'entreprise vises-tu ?"), "   ");
    await user.type(screen.getByLabelText("Quand veux-tu changer de poste ?"), " Dans 6 mois ");
    await user.click(screen.getByRole("button", { name: "Répondre" }));
    expect(onAnswer).toHaveBeenCalledWith({ answers: { q2: "Dans 6 mois" } });
  });

  it("does not send while every field is empty, but keeps the option usable", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={framing} answered={false} onAnswer={onAnswer} />);
    expect(screen.getByRole("button", { name: "Répondre" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Lancer la recherche" }));
    expect(onAnswer).toHaveBeenCalledWith("go");
  });

  it("sends the typed answers when the option is clicked, so they are never lost", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(<InterruptCard interrupt={framing} answered={false} onAnswer={onAnswer} />);
    await user.type(screen.getByLabelText("Quand veux-tu changer de poste ?"), " Dans 6 mois ");
    await user.click(screen.getByRole("button", { name: "Lancer la recherche" }));
    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer).toHaveBeenCalledWith({ answers: { q2: "Dans 6 mois" } });
  });

  it("waits for the required fields", async () => {
    const user = userEvent.setup();
    const required = {
      ...framing,
      fields: [{ id: "q1", label: "Ton objectif ?", max_length: 100, required: true }],
    };
    render(<InterruptCard interrupt={required} answered={false} onAnswer={vi.fn()} />);
    const field = screen.getByLabelText("Ton objectif ?");
    expect(field).toBeRequired();
    expect(field).toHaveAttribute("maxlength", "100");
    expect(screen.getByRole("button", { name: "Répondre" })).toBeDisabled();
    await user.type(field, "Devenir tech lead");
    expect(screen.getByRole("button", { name: "Répondre" })).toBeEnabled();
  });

  it("hides the framing fields once answered", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <InterruptCard interrupt={framing} answered={false} onAnswer={vi.fn()} />,
    );
    await user.type(screen.getByLabelText("Quand veux-tu changer de poste ?"), " Dans 6 mois ");
    rerender(<InterruptCard interrupt={framing} answered onAnswer={vi.fn()} />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
    // Les réponses saisies dans cet onglet restent lisibles, sans champ ; le champ vide est omis.
    expect(screen.getByText("Quand veux-tu changer de poste ?")).toBeInTheDocument();
    expect(screen.getByText("Dans 6 mois")).toBeInTheDocument();
    expect(screen.queryByText("Quel type d'entreprise vises-tu ?")).toBeNull();
  });

  it("shows only the question and the receipt when the answer was typed elsewhere", () => {
    render(<InterruptCard interrupt={framing} answered onAnswer={vi.fn()} />);
    expect(screen.getByText("Réponds aux questions de cadrage.")).toBeInTheDocument();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
    expect(screen.queryByText("Quel type d'entreprise vises-tu ?")).toBeNull();
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
