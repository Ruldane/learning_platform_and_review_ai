import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeWeek } from "../fixtures";
import { TaskList } from "./TaskList";

function setup(overrides: Partial<React.ComponentProps<typeof TaskList>> = {}) {
  const props = {
    weeks: [makeWeek()],
    editable: true,
    onToggleDone: vi.fn(),
    onDelete: vi.fn(),
    onAdd: vi.fn(),
    ...overrides,
  };
  render(<TaskList {...props} />);
  return props;
}

async function fillForm(user: ReturnType<typeof userEvent.setup>, minutes: string) {
  await user.type(screen.getByLabelText("Titre"), "Écrire un test");
  await user.selectOptions(screen.getByLabelText("Type"), "pratiquer");
  await user.clear(screen.getByLabelText("Durée (minutes)"));
  if (minutes) await user.type(screen.getByLabelText("Durée (minutes)"), minutes);
  await user.type(screen.getByLabelText("Critère de fin"), "Le test passe.");
  await user.selectOptions(screen.getByLabelText("Jour"), "2026-11-19");
}

describe("TaskList", () => {
  it("groups the tasks by week and module", () => {
    setup();
    expect(
      screen.getByRole("heading", { name: "Semaine 1 : Premiers pas en Python" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bases du langage" })).toBeInTheDocument();
    expect(screen.getByText("Pratiquer les boucles")).toBeInTheDocument();
    expect(screen.getAllByText(/Critère de fin : /).length).toBeGreaterThan(0);
  });

  it("toggles and deletes a task", async () => {
    const user = userEvent.setup();
    const props = setup();
    await user.click(
      screen.getByRole("checkbox", { name: "Marquer « Lire le chapitre 1 » comme faite" }),
    );
    expect(props.onToggleDone).toHaveBeenCalledWith("t1", true);
    await user.click(screen.getByRole("button", { name: "Supprimer « Lire le chapitre 1 »" }));
    expect(props.onDelete).toHaveBeenCalledWith("t1");
  });

  it("unchecks a task that is already done", async () => {
    const user = userEvent.setup();
    const props = setup();
    const box = screen.getByRole("checkbox", { name: "Marquer « Réviser les types » comme faite" });
    expect(box).toBeChecked();
    await user.click(box);
    expect(props.onToggleDone).toHaveBeenCalledWith("t3", false);
  });

  it("is read-only when not editable", () => {
    setup({ editable: false });
    expect(screen.getByRole("checkbox", { name: /Lire le chapitre 1/ })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.queryByLabelText("Titre")).toBeNull();
  });

  it("adds a task from the form", async () => {
    const user = userEvent.setup();
    const props = setup();
    await fillForm(user, "45");
    await user.click(screen.getByRole("button", { name: "Ajouter la tâche" }));
    expect(props.onAdd).toHaveBeenCalledWith({
      title: "Écrire un test",
      type: "pratiquer",
      minutes: 45,
      doneCriterion: "Le test passe.",
      plannedDate: "2026-11-19",
    });
  });

  it.each(["10", "121", "abc", "30.5", ""])("refuses a duration of %j", async (minutes) => {
    const user = userEvent.setup();
    const props = setup();
    await fillForm(user, minutes);
    await user.click(screen.getByRole("button", { name: "Ajouter la tâche" }));
    expect(props.onAdd).not.toHaveBeenCalled();
    expect(
      screen.getByText("La durée doit être un nombre entier de 15 à 120 minutes."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Durée (minutes)")).toBeInvalid();
  });

  it("accepts the bounds 15 and 120", async () => {
    const user = userEvent.setup();
    const props = setup();
    await fillForm(user, "15");
    await user.click(screen.getByRole("button", { name: "Ajouter la tâche" }));
    expect(props.onAdd).toHaveBeenCalledWith(expect.objectContaining({ minutes: 15 }));
  });

  it("explains each missing field next to it", async () => {
    const user = userEvent.setup();
    const props = setup();
    await user.click(screen.getByRole("button", { name: "Ajouter la tâche" }));
    expect(props.onAdd).not.toHaveBeenCalled();
    expect(screen.getByText("Donne un titre à la tâche.")).toBeInTheDocument();
    expect(screen.getByText("Indique à quoi on voit que la tâche est faite.")).toBeInTheDocument();
    expect(screen.getByText("Choisis le jour de la tâche.")).toBeInTheDocument();
  });

  it("shows a refusal coming from the server under the form", () => {
    setup({ addError: "La semaine dépasserait son plafond." });
    const form = screen.getByRole("form", { name: "Ajouter une tâche" });
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "La semaine dépasserait son plafond.",
    );
  });

  it("shows an empty state without tasks", () => {
    setup({ weeks: [] });
    expect(screen.getByText("Aucune tâche pour l'instant.")).toBeInTheDocument();
  });
});
