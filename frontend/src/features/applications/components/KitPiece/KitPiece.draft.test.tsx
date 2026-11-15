import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { piece, setup } from "./kitPieceTestkit";

describe("KitPiece, brouillon et enregistrement", () => {
  it("gives the focus back to the text January was editing, not to the first one", async () => {
    const { user } = setup(
      piece({ kind: "followups", content: "Courriel 7\n\n---\n\nCourriel 14" }),
    );
    await user.type(screen.getByLabelText("Relance à 14 jours"), "!");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Relances" }));
    await waitFor(() => expect(screen.getByLabelText("Relance à 14 jours")).toHaveFocus());
  });

  it("keeps showing the saved text until the kit is read again, never the old one", async () => {
    const { user, rerender } = setup(piece());
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), " Merci.");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    await screen.findByText(/Modification enregistrée/);
    const field = screen.getByLabelText("Texte : Lettre de motivation");
    expect(field).toHaveValue("Bonjour,\n\nCordialement Merci.");
    expect(
      screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" }),
    ).toBeDisabled();
    rerender(piece({ content: "Bonjour,\n\nCordialement Merci.", edited: true }));
    expect(field).toHaveValue("Bonjour,\n\nCordialement Merci.");
    // Une nouvelle version du serveur, plus tard, remplace le texte (plus de brouillon).
    rerender(piece({ content: "Refaite par le kit.", edited: false }));
    expect(field).toHaveValue("Refaite par le kit.");
  });

  it("does not repeat the blank marker as a placeholder", () => {
    setup(
      piece({
        kind: "form_answers",
        status: "to_check",
        salaryFields: 1,
        content: "### Prétentions ?\nÀ remplir par toi",
      }),
    );
    expect(screen.getByLabelText("Prétentions ?")).not.toHaveAttribute("placeholder");
  });

  it("titles each piece at level 2, under the level-1 title of the page", () => {
    setup(piece());
    expect(screen.getByRole("heading", { level: 2, name: "Lettre de motivation" })).toBeVisible();
  });

  it("says a saved empty piece is empty, not just « à vérifier »", () => {
    setup(piece({ status: "to_check", content: "" }));
    expect(screen.getByRole("note")).toHaveTextContent("Cette pièce est vide");
  });

  it("limits the text to what the server accepts and refuses to save a longer one", async () => {
    const { onSave } = setup(piece({ kind: "followups", content: "A\n\n---\n\nB" }));
    const first = screen.getByLabelText("Relance à 7 jours");
    expect(first).toHaveAttribute("maxLength", "20000");
    fireEvent.change(first, { target: { value: "x".repeat(20_000) } });
    fireEvent.change(screen.getByLabelText("Relance à 14 jours"), { target: { value: "y" } });
    expect(await screen.findByText(/dépasse 20 000 caractères/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Enregistrer : Relances" })).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });
});
