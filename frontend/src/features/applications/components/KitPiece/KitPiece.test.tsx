import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { KitSaveResult } from "../viewTypes";
import { KitPiece } from "./KitPiece";
import { piece, setup } from "./kitPieceTestkit";

const COVER_TEXT = "Text: Cover letter";
const COVER_COPY = "Copy: Cover letter";
const COVER_SAVE = "Save: Cover letter";

describe("KitPiece", () => {
  it("shows the title, the status in words, the word count and the text", () => {
    setup(piece());
    const section = screen.getByRole("region", { name: "Cover letter" });
    expect(within(section).getByText("Ready")).toBeVisible();
    expect(within(section).getByText("120 words")).toBeVisible();
    expect(within(section).getByLabelText(COVER_TEXT)).toHaveValue(
      "Bonjour,\n\nCordialement",
    );
  });

  it("copies what is shown, edits included, and says so", async () => {
    const { user, onCopy } = setup(piece());
    const text = screen.getByLabelText(COVER_TEXT);
    await user.clear(text);
    await user.type(text, "Mon texte");
    await user.click(screen.getByRole("button", { name: COVER_COPY }));
    expect(onCopy).toHaveBeenCalledWith("Mon texte");
    expect(await screen.findByText("Copied to clipboard.")).toBeVisible();
  });

  it("says when the copy is impossible", async () => {
    const { user } = setup(piece(), { copy: () => Promise.reject(new Error("no")) });
    await user.click(screen.getByRole("button", { name: COVER_COPY }));
    expect(await screen.findByText(/Can't copy/)).toBeVisible();
  });

  it("explains a piece to check by the terms the profile does not say", () => {
    setup(piece({ status: "to_check", flags: ["Kubernetes", "5"] }));
    const note = screen.getByRole("note");
    expect(note).toHaveTextContent("Not in your profile: Kubernetes, 5.");
    expect(screen.getByText("To check")).toBeVisible();
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
    expect(screen.getByRole("note")).toHaveTextContent(/1 salary answer is for you to fill in/);
    const salary = screen.getByLabelText("Prétentions salariales ?");
    expect(salary).toHaveValue("");
    expect(salary).toHaveAccessibleDescription("For you to fill in");
    expect(screen.getByLabelText("Pourquoi nous ?")).toHaveValue("Parce que.");
  });

  it("marks unsupported answers as To complete", () => {
    setup(
      piece({
        kind: "form_answers",
        status: "to_check",
        content: "### Votre expérience Kubernetes ?\nÀ compléter",
      }),
    );
    expect(screen.getByRole("note")).toHaveTextContent(/1 answer needs completing/);
    expect(screen.getByLabelText("Votre expérience Kubernetes ?")).toHaveAccessibleDescription(
      "To complete",
    );
  });

  it("explains a company brief to check with no flag: sections without a source were removed", () => {
    setup(piece({ kind: "company_brief", status: "to_check", content: "Acme [1]" }));
    expect(screen.getByRole("note")).toHaveTextContent(/Unsourced passages were removed/);
  });

  it("falls back to a general reason when nothing else explains it", () => {
    setup(piece({ status: "to_check" }));
    expect(screen.getByRole("note")).toHaveTextContent("reread it before using it");
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
      "[1] Page A (opens in a new tab)",
      "[2] example.org/b (opens in a new tab)",
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
      "This piece couldn't be produced: Le modèle n'a pas répondu.",
    );
    expect(screen.getByText("Failed")).toBeVisible();
    await user.type(screen.getByLabelText(COVER_TEXT), "Ma lettre");
    await user.click(screen.getByRole("button", { name: COVER_SAVE }));
    expect(onSave).toHaveBeenCalledWith("Ma lettre");
  });

  it("shows a piece that has not arrived yet, preparing while the kit runs, without any field", () => {
    const { rerender } = setup(piece({ status: "pending", content: "", words: null }), {
      running: true,
    });
    expect(screen.getByText("Preparing…")).toBeVisible();
    expect(screen.queryByRole("textbox")).toBeNull();
    rerender(piece({ status: "pending", content: "", words: null }));
    expect(screen.getByText("Preparing…")).toBeVisible();
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
    expect(screen.getByText("Not produced yet")).toBeVisible();
    expect(screen.queryByRole("button", { name: /Save/ })).toBeNull();
  });

  it("saves only on request: the button waits for a change, then sends the whole text", async () => {
    const { user, onSave } = setup(piece());
    const save = screen.getByRole("button", { name: COVER_SAVE });
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText(COVER_TEXT), " Merci.");
    expect(screen.getByText("Change not saved yet.")).toBeVisible();
    expect(onSave).not.toHaveBeenCalled();
    await user.click(save);
    expect(onSave).toHaveBeenCalledWith("Bonjour,\n\nCordialement Merci.");
    expect(await screen.findByText("Change saved. The piece is ready.")).toBeVisible();
    expect(screen.getByLabelText(COVER_TEXT)).toHaveFocus();
  });

  it("says the piece stays to check when the server re-reads it so", async () => {
    const { user } = setup(piece({ status: "to_check", flags: ["Kubernetes"] }), {
      save: { ok: true, status: "to_check" },
    });
    await user.type(screen.getByLabelText(COVER_TEXT), "!");
    await user.click(screen.getByRole("button", { name: COVER_SAVE }));
    expect(await screen.findByText(/still needs checking/)).toBeVisible();
  });

  it("shows the refusal and keeps the draft", async () => {
    const { user } = setup(piece(), { save: { ok: false, message: "Profil introuvable." } });
    await user.type(screen.getByLabelText(COVER_TEXT), "!");
    await user.click(screen.getByRole("button", { name: COVER_SAVE }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Profil introuvable.");
    expect(screen.getByLabelText(COVER_TEXT)).toHaveValue(
      "Bonjour,\n\nCordialement!",
    );
  });

  it("shows separate follow-up fields and saves their combined text", async () => {
    const { user, onCopy, onSave } = setup(
      piece({ kind: "followups", content: "Courriel 7\n\n---\n\nCourriel 14" }),
    );
    expect(screen.getByLabelText("Follow-up after 7 days")).toHaveValue("Courriel 7");
    expect(screen.getByLabelText("Follow-up after 14 days")).toHaveValue("Courriel 14");
    await user.click(screen.getByRole("button", { name: "Copy: Follow-up after 14 days" }));
    expect(onCopy).toHaveBeenCalledWith("Courriel 14");
    await user.type(screen.getByLabelText("Follow-up after 7 days"), "!");
    await user.click(screen.getByRole("button", { name: "Save: Follow-ups" }));
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
    await user.click(screen.getByRole("button", { name: "Save: Form answers" }));
    expect(onSave).toHaveBeenCalledWith(
      "### Pourquoi nous ?\nParce que.!\n\n### Prétentions ?\nÀ remplir par toi",
    );
    // Entering an answer removes the blank marker from the field's description.
    await user.type(screen.getByLabelText("Prétentions ?"), "45 k€");
    expect(screen.getByLabelText("Prétentions ?")).not.toHaveAccessibleDescription();
  });

  it("keeps the draft when the kit is read again with a new text, and says so", async () => {
    const { user, rerender } = setup(piece());
    await user.type(screen.getByLabelText(COVER_TEXT), " Merci.");
    rerender(piece({ content: "Nouvelle version du serveur" }));
    expect(screen.getByLabelText(COVER_TEXT)).toHaveValue(
      "Bonjour,\n\nCordialement Merci.",
    );
    expect(screen.getByText(/your draft is kept/)).toBeVisible();
  });

  it("shows the new text of the server when January has not touched the piece", () => {
    const { rerender } = setup(piece());
    rerender(piece({ content: "Nouvelle version du serveur", status: "to_check", flags: ["Go"] }));
    expect(screen.getByLabelText(COVER_TEXT)).toHaveValue(
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
    expect(screen.getByText("Edited by you")).toBeVisible();
    await user.type(screen.getByLabelText(COVER_TEXT), "!");
    await user.click(screen.getByRole("button", { name: COVER_SAVE }));
    expect(screen.getByLabelText(COVER_TEXT)).toHaveAttribute("readonly");
    finish({ ok: true, status: "ready" });
    await waitFor(() =>
      expect(screen.getByLabelText(COVER_TEXT)).not.toHaveAttribute("readonly"),
    );
  });
});
