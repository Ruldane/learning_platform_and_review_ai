import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ModificationView } from "../viewTypes";
import { ModificationCard } from "./ModificationCard";

const mod = (patch: Partial<ModificationView> = {}): ModificationView => ({
  id: "m1",
  ref: "m1",
  section: "experience",
  action: "rewrite",
  type: "impact",
  before: "Gère une équipe de 4 personnes",
  after: "Dirige une équipe de 4 personnes",
  reason: "Un verbe d'action plus fort.",
  status: "proposed",
  blocks: [],
  author: "writer",
  facts: [{ id: "x1a2", label: "Chef d'équipe chez Société Fictive" }],
  ...patch,
});

function setup(patch: Partial<ModificationView> = {}, busy = false) {
  const onDecide = vi.fn();
  const view = render(<ModificationCard mod={mod(patch)} onDecide={onDecide} busy={busy} />);
  return { onDecide, ...view };
}

describe("ModificationCard", () => {
  it("marks the addition and the removal without relying on colour", () => {
    const { container } = setup();
    const added = container.querySelector("ins");
    const removed = container.querySelector("del");
    expect(added).toHaveTextContent("Dirige");
    expect(removed).toHaveTextContent("Gère");
    expect(added).toHaveTextContent("ajouté");
    expect(removed).toHaveTextContent("retiré");
  });

  it("shows the reason, the type, the author and the facts it rests on", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Impact · Réécriture" })).toBeInTheDocument();
    expect(screen.getByText("Un verbe d'action plus fort.")).toBeInTheDocument();
    expect(screen.getByText("Proposée par Rédacteur")).toBeInTheDocument();
    expect(screen.getByText("S'appuie sur :")).toBeInTheDocument();
    expect(screen.getByText("Chef d'équipe chez Société Fictive")).toBeInTheDocument();
  });

  it("says when a line is added or removed", () => {
    setup({ action: "add", before: "", after: "Pilote la migration" });
    expect(screen.getByText("Rien : ligne ajoutée.")).toBeInTheDocument();
  });

  it("accepts and refuses a plain proposal", async () => {
    const { onDecide } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Accepter" }));
    expect(onDecide).toHaveBeenLastCalledWith("accepted");
    await userEvent.click(screen.getByRole("button", { name: "Refuser" }));
    expect(onDecide).toHaveBeenLastCalledWith("refused");
  });

  it("keeps Accept disabled for a to-confirm modification until the box is ticked", async () => {
    const { onDecide } = setup({
      status: "to_confirm",
      blocks: ["Le chiffre « 30 % » n'est pas dans ton profil."],
    });
    const group = screen.getByRole("group", { name: "À confirmer" });
    expect(within(group).getByText("Le chiffre « 30 % » n'est pas dans ton profil.")).toBeVisible();
    const accept = screen.getByRole("button", { name: "Accepter" });
    expect(accept).toBeDisabled();
    await userEvent.click(accept);
    expect(onDecide).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("checkbox", { name: "Je confirme que c'est vrai" }));
    expect(accept).toBeEnabled();
    await userEvent.click(accept);
    expect(onDecide).toHaveBeenCalledWith("accepted", { confirm: true });
  });

  it("asks for the confirmation again when the text changes", async () => {
    const onDecide = vi.fn();
    const base = mod({ status: "to_confirm" });
    const { rerender } = render(<ModificationCard mod={base} onDecide={onDecide} busy={false} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: "Accepter" })).toBeEnabled();
    rerender(
      <ModificationCard
        mod={{ ...base, after: "Dirige 6 personnes" }}
        onDecide={onDecide}
        busy={false}
      />,
    );
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Accepter" })).toBeDisabled();
  });

  it("returns the edited text from Modifier", async () => {
    const { onDecide } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const field = screen.getByRole("textbox", { name: "Texte modifié" });
    expect(field).toHaveValue("Dirige une équipe de 4 personnes");
    await userEvent.clear(field);
    await userEvent.type(field, "Encadre quatre personnes");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer et accepter" }));
    expect(onDecide).toHaveBeenCalledWith("accepted", { after: "Encadre quatre personnes" });
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("can cancel an edit and refuses an empty text", async () => {
    const { onDecide } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    await userEvent.clear(screen.getByRole("textbox"));
    expect(screen.getByRole("button", { name: "Enregistrer et accepter" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(onDecide).not.toHaveBeenCalled();
  });

  it("sends an edited to-confirm text without the confirmation: the back checks it again", async () => {
    const { onDecide } = setup({ status: "to_confirm" });
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const field = screen.getByRole("textbox", { name: "Texte modifié" });
    await userEvent.clear(field);
    await userEvent.type(field, "Dirige 6 personnes");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer et accepter" }));
    expect(onDecide).toHaveBeenCalledWith("accepted", { after: "Dirige 6 personnes" });
  });

  it("keeps the confirmation for the unedited text of a to-confirm modification", async () => {
    const { onDecide } = setup({ status: "to_confirm" });
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const save = screen.getByRole("button", { name: "Enregistrer et accepter" });
    expect(save).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: "Je confirme que c'est vrai" }));
    await userEvent.click(save);
    expect(onDecide).toHaveBeenCalledWith("accepted", {
      after: "Dirige une équipe de 4 personnes",
      confirm: true,
    });
  });

  it("offers « Modifier » only for a rewrite or an addition", () => {
    const { unmount } = setup({ action: "remove", before: "Ligne", after: "" });
    expect(screen.queryByRole("button", { name: "Modifier" })).toBeNull();
    unmount();
    const moved = setup({ action: "move" });
    expect(screen.queryByRole("button", { name: "Modifier" })).toBeNull();
    moved.unmount();
    setup({ action: "add", before: "", after: "Pilote la migration" });
    expect(screen.getByRole("button", { name: "Modifier" })).toBeInTheDocument();
  });

  it("keeps the editor open with the typed text when the decision is refused", async () => {
    const onDecide = vi.fn().mockResolvedValue(false);
    render(
      <ModificationCard
        mod={mod()}
        onDecide={onDecide}
        busy={false}
        error="Ce mot clé n'est pas dans ton profil."
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const field = screen.getByRole("textbox", { name: "Texte modifié" });
    await userEvent.clear(field);
    await userEvent.type(field, "Dirige une équipe sur AWS");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer et accepter" }));
    await waitFor(() => expect(onDecide).toHaveBeenCalled());
    expect(screen.getByRole("textbox", { name: "Texte modifié" })).toHaveValue(
      "Dirige une équipe sur AWS",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Ce mot clé n'est pas dans ton profil.");
  });

  it("closes the editor once the decision is taken", async () => {
    const onDecide = vi.fn().mockResolvedValue(true);
    render(<ModificationCard mod={mod()} onDecide={onDecide} busy={false} />);
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    await userEvent.type(screen.getByRole("textbox"), " bien");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer et accepter" }));
    await waitFor(() => expect(screen.queryByRole("textbox")).not.toBeInTheDocument());
  });

  it("says when an accepted line could not be placed in the generated version", () => {
    setup({ status: "accepted", ignoredIn: 2 });
    expect(screen.getByText("Non placée dans la version 2")).toBeInTheDocument();
  });

  it("locks every button while a decision is on its way", () => {
    setup({ status: "to_confirm" }, true);
    for (const name of ["Accepter", "Refuser", "Modifier"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    expect(screen.getByRole("checkbox")).toBeDisabled();
  });

  it("does not offer to accept what is already accepted", () => {
    setup({ status: "accepted" });
    expect(screen.getByRole("button", { name: "Accepter" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refuser" })).toBeEnabled();
  });

  it("is reachable by keyboard: tab order follows the box then the buttons", async () => {
    setup({ status: "to_confirm" });
    await userEvent.tab();
    expect(screen.getByRole("checkbox")).toHaveFocus();
    await userEvent.keyboard(" ");
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Accepter" })).toHaveFocus();
  });
});
