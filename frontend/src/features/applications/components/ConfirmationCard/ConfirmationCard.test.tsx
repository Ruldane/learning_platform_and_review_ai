import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ConfirmationView } from "../viewTypes";
import { ConfirmationCard } from "./ConfirmationCard";

const field = (id: string, label: string, value: string, required = false) => ({
  id,
  label,
  required,
  maxLength: 200,
  value,
});

const CONFIRMATION: ConfirmationView = {
  question: "Je crée cette fiche ?",
  fields: [
    field("company", "Entreprise", "Acme", true),
    field("title", "Poste", "Data engineer", true),
    field("status", "Statut", "applied", true),
    field("applied_on", "Date de candidature (AAAA-MM-JJ)", ""),
    field("channel", "Canal", "linkedin"),
    field("contact_name", "Contact", ""),
    field("contact_role", "Rôle du contact", ""),
    field("notes", "Notes", ""),
  ],
  options: [
    { value: "create", label: "Créer la fiche" },
    { value: "cancel", label: "Annuler" },
  ],
};

function setup(confirmation = CONFIRMATION, disabled = false) {
  const onChoose = vi.fn();
  render(<ConfirmationCard confirmation={confirmation} disabled={disabled} onChoose={onChoose} />);
  return onChoose;
}

describe("ConfirmationCard", () => {
  it("shows the question and the fields the assistant read, already filled", () => {
    setup();
    expect(screen.getByText("Je crée cette fiche ?")).toBeInTheDocument();
    expect(screen.getByLabelText("Entreprise")).toHaveValue("Acme");
    expect(screen.getByLabelText("Poste")).toHaveValue("Data engineer");
  });

  it("shows the status and the channel in French, not as codes", () => {
    setup();
    expect(screen.getByLabelText("Statut")).toHaveDisplayValue("Postulée");
    expect(screen.getByLabelText("Canal")).toHaveDisplayValue("LinkedIn");
  });

  it("says an empty date means today", () => {
    setup();
    expect(screen.getByLabelText("Date de candidature (AAAA-MM-JJ)")).toHaveAccessibleDescription(
      "Sans date, la fiche prend la date d'aujourd'hui.",
    );
  });

  it("sends the choice with the fields as January leaves them", async () => {
    const user = userEvent.setup();
    const onChoose = setup();
    const company = screen.getByLabelText("Entreprise");
    await user.clear(company);
    await user.type(company, "Acme Corp");
    await user.selectOptions(screen.getByLabelText("Statut"), "interview");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    expect(onChoose).toHaveBeenCalledWith(
      "create",
      expect.objectContaining({
        company: "Acme Corp",
        status: "interview",
        title: "Data engineer",
      }),
    );
  });

  it("refuses to create while a required field is empty, but never blocks cancel", async () => {
    const user = userEvent.setup();
    const onChoose = setup();
    await user.clear(screen.getByLabelText("Poste"));
    expect(screen.getByRole("button", { name: "Créer la fiche" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Annuler" }));
    expect(onChoose).toHaveBeenCalledWith("cancel", {});
  });

  it("offers only the choices of the server", () => {
    setup({
      ...CONFIRMATION,
      options: [
        { value: "distinct", label: "C'est un autre poste" },
        { value: "open", label: "Ouvrir la fiche existante" },
        { value: "cancel", label: "Annuler" },
      ],
    });
    expect(screen.queryByRole("button", { name: "Créer la fiche" })).toBeNull();
    expect(screen.getByRole("button", { name: "C'est un autre poste" })).toBeEnabled();
  });

  it("sends the fields with « C'est un autre poste » and none with « Ouvrir »", async () => {
    const user = userEvent.setup();
    const onChoose = setup({
      ...CONFIRMATION,
      options: [
        { value: "distinct", label: "C'est un autre poste" },
        { value: "open", label: "Ouvrir la fiche existante" },
      ],
    });
    await user.click(screen.getByRole("button", { name: "Ouvrir la fiche existante" }));
    await user.click(screen.getByRole("button", { name: "C'est un autre poste" }));
    expect(onChoose).toHaveBeenNthCalledWith(1, "open", {});
    expect(onChoose).toHaveBeenNthCalledWith(
      2,
      "distinct",
      expect.objectContaining({ company: "Acme" }),
    );
  });

  it("disables everything when it is answered", () => {
    setup(CONFIRMATION, true);
    expect(screen.getByLabelText("Entreprise")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Annuler" })).toBeDisabled();
  });
});
