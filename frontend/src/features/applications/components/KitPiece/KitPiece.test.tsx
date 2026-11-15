import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { KitSaveResult } from "../viewTypes";
import { KitPiece } from "./KitPiece";
import { piece, setup } from "./kitPieceTestkit";

describe("KitPiece", () => {
  it("shows the title, the status in words, the word count and the text", () => {
    setup(piece());
    const section = screen.getByRole("region", { name: "Lettre de motivation" });
    expect(within(section).getByText("Prête")).toBeVisible();
    expect(within(section).getByText("120 mots")).toBeVisible();
    expect(within(section).getByLabelText("Texte : Lettre de motivation")).toHaveValue(
      "Bonjour,\n\nCordialement",
    );
  });

  it("copies what is shown, edits included, and says so", async () => {
    const { user, onCopy } = setup(piece());
    const text = screen.getByLabelText("Texte : Lettre de motivation");
    await user.clear(text);
    await user.type(text, "Mon texte");
    await user.click(screen.getByRole("button", { name: "Copier : Lettre de motivation" }));
    expect(onCopy).toHaveBeenCalledWith("Mon texte");
    expect(await screen.findByText("Copié dans le presse-papiers.")).toBeVisible();
  });

  it("says when the copy is impossible", async () => {
    const { user } = setup(piece(), { copy: () => Promise.reject(new Error("no")) });
    await user.click(screen.getByRole("button", { name: "Copier : Lettre de motivation" }));
    expect(await screen.findByText(/Copie impossible/)).toBeVisible();
  });

  it("explains a piece to check by the terms the profile does not say", () => {
    setup(piece({ status: "to_check", flags: ["Kubernetes", "5"] }));
    const note = screen.getByRole("note");
    expect(note).toHaveTextContent("Absent de ton profil : Kubernetes, 5.");
    expect(screen.getByText("À vérifier")).toBeVisible();
  });

  it("explains a form to check with no flag: the salary answers left to January", () => {
    setup(
      piece({
        kind: "form_answers",
        status: "to_check",
        salaryFields: 1,
        content:
          "### Pourquoi nous ?\nParce que.\n\n### Prétentions salariales ?\nÀ remplir par toi",
      }),
    );
    expect(screen.getByRole("note")).toHaveTextContent(/1 réponse salariale est à remplir par toi/);
    const salary = screen.getByLabelText("Prétentions salariales ?");
    expect(salary).toHaveValue("");
    expect(salary).toHaveAccessibleDescription("À remplir par toi");
    expect(screen.getByLabelText("Pourquoi nous ?")).toHaveValue("Parce que.");
  });

  it("names the answers the profile does not back as « à compléter »", () => {
    setup(
      piece({
        kind: "form_answers",
        status: "to_check",
        content: "### Votre expérience Kubernetes ?\nÀ compléter",
      }),
    );
    expect(screen.getByRole("note")).toHaveTextContent(/1 réponse est à compléter/);
    expect(screen.getByLabelText("Votre expérience Kubernetes ?")).toHaveAccessibleDescription(
      "À compléter",
    );
  });

  it("explains a company brief to check with no flag: sections without a source were removed", () => {
    setup(piece({ kind: "company_brief", status: "to_check", content: "Acme [1]" }));
    expect(screen.getByRole("note")).toHaveTextContent(/passages sans source ont été retirés/);
  });

  it("falls back to a general reason when nothing else explains it", () => {
    setup(piece({ status: "to_check" }));
    expect(screen.getByRole("note")).toHaveTextContent("relis-la avant de t'en servir");
  });

  it("lists the sources of the brief as links that open in a new tab, in citation order", () => {
    setup(
      piece({
        kind: "company_brief",
        content: "Acme fait de la data [1] et du cloud [2].",
        sources: [
          { rank: 2, url: "https://example.org/b", title: null },
          { rank: 1, url: "https://example.org/a", title: "Page A" },
          { rank: 3, url: "javascript:alert(1)", title: "Piège" },
        ],
      }),
    );
    const list = screen.getByRole("list");
    const items = within(list).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "[1] Page A (s'ouvre dans un nouvel onglet)",
      "[2] example.org/b (s'ouvre dans un nouvel onglet)",
      "[3] Piège",
    ]);
    const first = within(items[0]!).getByRole("link");
    expect(first).toHaveAttribute("href", "https://example.org/a");
    expect(first).toHaveAttribute("target", "_blank");
    expect(first).toHaveAttribute("rel", "noopener noreferrer");
    expect(within(items[2]!).queryByRole("link")).toBeNull();
  });

  it("shows the reason of a failed piece and lets January write it herself", async () => {
    const { user, onSave } = setup(
      piece({ status: "failed", content: "", error: "Le modèle n'a pas répondu.", words: null }),
    );
    expect(screen.getByRole("note")).toHaveTextContent(
      "Cette pièce n'a pas pu être produite : Le modèle n'a pas répondu.",
    );
    expect(screen.getByText("Échec")).toBeVisible();
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), "Ma lettre");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    expect(onSave).toHaveBeenCalledWith("Ma lettre");
  });

  it("shows a piece that has not arrived yet, preparing while the kit runs, without any field", () => {
    const { rerender } = setup(piece({ status: "pending", content: "", words: null }), {
      running: true,
    });
    expect(screen.getByText("En préparation…")).toBeVisible();
    expect(screen.queryByRole("textbox")).toBeNull();
    rerender(piece({ status: "pending", content: "", words: null }));
    expect(screen.getByText("En préparation…")).toBeVisible();
  });

  it("says a piece is not produced yet when the kit is not running", () => {
    render(
      <KitPiece
        piece={piece({ status: "pending", content: "", words: null })}
        running={false}
        onSave={() => Promise.resolve({ ok: true, status: "ready" })}
        onCopy={() => undefined}
      />,
    );
    expect(screen.getByText("Pas encore produite")).toBeVisible();
    expect(screen.queryByRole("button", { name: /Enregistrer/ })).toBeNull();
  });

  it("saves only on request: the button waits for a change, then sends the whole text", async () => {
    const { user, onSave } = setup(piece());
    const save = screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" });
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), " Merci.");
    expect(screen.getByText("Modification pas encore enregistrée.")).toBeVisible();
    expect(onSave).not.toHaveBeenCalled();
    await user.click(save);
    expect(onSave).toHaveBeenCalledWith("Bonjour,\n\nCordialement Merci.");
    expect(await screen.findByText("Modification enregistrée. La pièce est prête.")).toBeVisible();
    expect(screen.getByLabelText("Texte : Lettre de motivation")).toHaveFocus();
  });

  it("says the piece stays to check when the server re-reads it so", async () => {
    const { user } = setup(piece({ status: "to_check", flags: ["Kubernetes"] }), {
      save: { ok: true, status: "to_check" },
    });
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), "!");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    expect(await screen.findByText(/La pièce reste à vérifier/)).toBeVisible();
  });

  it("shows the refusal and keeps the draft", async () => {
    const { user } = setup(piece(), { save: { ok: false, message: "Profil introuvable." } });
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), "!");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Profil introuvable.");
    expect(screen.getByLabelText("Texte : Lettre de motivation")).toHaveValue(
      "Bonjour,\n\nCordialement!",
    );
  });

  it("shows the two follow-ups as two blocks, each with its own Copier, and saves them joined", async () => {
    const { user, onCopy, onSave } = setup(
      piece({ kind: "followups", content: "Courriel 7\n\n---\n\nCourriel 14" }),
    );
    expect(screen.getByLabelText("Relance à 7 jours")).toHaveValue("Courriel 7");
    expect(screen.getByLabelText("Relance à 14 jours")).toHaveValue("Courriel 14");
    await user.click(screen.getByRole("button", { name: "Copier : Relance à 14 jours" }));
    expect(onCopy).toHaveBeenCalledWith("Courriel 14");
    await user.type(screen.getByLabelText("Relance à 7 jours"), "!");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Relances" }));
    expect(onSave).toHaveBeenCalledWith("Courriel 7!\n\n---\n\nCourriel 14");
  });

  it("saves a form with the blank answer put back as the marker the server knows", async () => {
    const { user, onSave } = setup(
      piece({
        kind: "form_answers",
        status: "to_check",
        salaryFields: 1,
        content: "### Pourquoi nous ?\nParce que.\n\n### Prétentions ?\nÀ remplir par toi",
      }),
    );
    await user.type(screen.getByLabelText("Pourquoi nous ?"), "!");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Réponses au formulaire" }));
    expect(onSave).toHaveBeenCalledWith(
      "### Pourquoi nous ?\nParce que.!\n\n### Prétentions ?\nÀ remplir par toi",
    );
    // Remplie par January, la réponse n'est plus marquée.
    await user.type(screen.getByLabelText("Prétentions ?"), "45 k€");
    expect(screen.getByLabelText("Prétentions ?")).not.toHaveAccessibleDescription();
  });

  it("keeps the draft when the kit is read again with a new text, and says so", async () => {
    const { user, rerender } = setup(piece());
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), " Merci.");
    rerender(piece({ content: "Nouvelle version du serveur" }));
    expect(screen.getByLabelText("Texte : Lettre de motivation")).toHaveValue(
      "Bonjour,\n\nCordialement Merci.",
    );
    expect(screen.getByText(/ton brouillon est gardé/)).toBeVisible();
  });

  it("shows the new text of the server when January has not touched the piece", () => {
    const { rerender } = setup(piece());
    rerender(piece({ content: "Nouvelle version du serveur", status: "to_check", flags: ["Go"] }));
    expect(screen.getByLabelText("Texte : Lettre de motivation")).toHaveValue(
      "Nouvelle version du serveur",
    );
  });

  it("marks a piece January edited, and freezes the text while it saves", async () => {
    let finish: (value: KitSaveResult) => void = () => undefined;
    const onSave = vi.fn(() => new Promise<KitSaveResult>((resolve) => (finish = resolve)));
    const user = userEvent.setup();
    render(
      <KitPiece
        piece={piece({ edited: true })}
        running={false}
        onSave={onSave}
        onCopy={() => undefined}
      />,
    );
    expect(screen.getByText("Modifiée par toi")).toBeVisible();
    await user.type(screen.getByLabelText("Texte : Lettre de motivation"), "!");
    await user.click(screen.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    expect(screen.getByLabelText("Texte : Lettre de motivation")).toHaveAttribute("readonly");
    finish({ ok: true, status: "ready" });
    await waitFor(() =>
      expect(screen.getByLabelText("Texte : Lettre de motivation")).not.toHaveAttribute("readonly"),
    );
  });
});
