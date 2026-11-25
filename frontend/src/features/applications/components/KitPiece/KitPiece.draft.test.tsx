import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { piece, setup } from "./kitPieceTestkit";

describe("KitPiece drafts and saving", () => {
  it("gives the focus back to the text January was editing, not to the first one", async () => {
    const { user } = setup(
      piece({ kind: "followups", content: "Courriel 7\n\n---\n\nCourriel 14" }),
    );
    await user.type(screen.getByLabelText("Follow-up after 14 days"), "!");
    await user.click(screen.getByRole("button", { name: "Save: Follow-ups" }));
    await waitFor(() => expect(screen.getByLabelText("Follow-up after 14 days")).toHaveFocus());
  });

  it("keeps showing the saved text until the kit is read again, never the old one", async () => {
    const { user, rerender } = setup(piece());
    await user.type(screen.getByLabelText("Text: Cover letter"), " Merci.");
    await user.click(screen.getByRole("button", { name: "Save: Cover letter" }));
    await screen.findByText(/Change saved/);
    const field = screen.getByLabelText("Text: Cover letter");
    expect(field).toHaveValue("Bonjour,\n\nCordialement Merci.");
    expect(
      screen.getByRole("button", { name: "Save: Cover letter" }),
    ).toBeDisabled();
    rerender(piece({ content: "Bonjour,\n\nCordialement Merci.", edited: true }));
    expect(field).toHaveValue("Bonjour,\n\nCordialement Merci.");
    // The next server version replaces the text once the draft is saved.
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
    expect(screen.getByRole("heading", { level: 2, name: "Cover letter" })).toBeVisible();
  });

  it("explains when a saved piece is empty", () => {
    setup(piece({ status: "to_check", content: "" }));
    expect(screen.getByRole("note")).toHaveTextContent("This piece is empty");
  });

  it("limits the text to what the server accepts and refuses to save a longer one", async () => {
    const { onSave } = setup(piece({ kind: "followups", content: "A\n\n---\n\nB" }));
    const first = screen.getByLabelText("Follow-up after 7 days");
    expect(first).toHaveAttribute("maxLength", "20000");
    fireEvent.change(first, { target: { value: "x".repeat(20_000) } });
    fireEvent.change(screen.getByLabelText("Follow-up after 14 days"), { target: { value: "y" } });
    expect(await screen.findByText(/over 20,000 characters/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Save: Follow-ups" })).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });
});
