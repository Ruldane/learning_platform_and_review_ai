import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DraftView } from "../viewTypes";
import { DraftCard } from "./DraftCard";

const DRAFT: DraftView = {
  kind: "linkedin_post",
  content: "J'ai construit un pipeline SQL.",
  status: "ready",
  flags: [],
  edited: false,
};

function setup(draft: DraftView = DRAFT, onCopy: () => void | Promise<void> = vi.fn()) {
  const onSave = vi.fn();
  const view = render(<DraftCard draft={draft} onSave={onSave} onCopy={onCopy} />);
  return { onSave, onCopy, user: userEvent.setup(), ...view };
}

describe("DraftCard", () => {
  it("shows the kind and the text in an editable field", () => {
    setup();
    expect(screen.getByLabelText("Post LinkedIn")).toHaveValue("J'ai construit un pipeline SQL.");
  });

  it("lists the flagged terms as given, joined with a comma, under « À vérifier »", () => {
    setup({ ...DRAFT, status: "to_check", flags: ["10000", "Kubernetes"] });
    expect(screen.getByRole("note")).toHaveTextContent(
      "À vérifier : absent de ton profil et de ton rendu : 10000, Kubernetes",
    );
  });

  it("shows a plain warning when a draft is to check without any term", () => {
    setup({ ...DRAFT, status: "to_check", flags: [] });
    expect(screen.getByRole("note")).toHaveTextContent("À vérifier avant de l'utiliser.");
  });

  it("shows no warning for a draft that is ready", () => {
    setup();
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("saves the edited text, and only once it differs from the saved one", async () => {
    const { onSave, user } = setup();
    const save = screen.getByRole("button", { name: "Enregistrer" });
    expect(save).toHaveAttribute("aria-disabled", "true");
    await user.type(screen.getByLabelText("Post LinkedIn"), " Merci !");
    expect(save).toHaveAttribute("aria-disabled", "false");
    await user.click(save);
    expect(onSave).toHaveBeenCalledWith("J'ai construit un pipeline SQL. Merci !");
  });

  it("takes the new text when the saved draft changes", () => {
    const { rerender, onSave, onCopy } = setup();
    rerender(
      <DraftCard
        draft={{ ...DRAFT, content: "Texte enregistré.", edited: true }}
        onSave={onSave}
        onCopy={onCopy}
      />,
    );
    expect(screen.getByLabelText("Post LinkedIn")).toHaveValue("Texte enregistré.");
    expect(screen.getByText("Retouché par toi")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enregistrer" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("copies the text on screen, including edits, and confirms in a status region", async () => {
    const { onCopy, user } = setup(DRAFT, vi.fn().mockResolvedValue(undefined));
    await user.type(screen.getByLabelText("Post LinkedIn"), "!");
    await user.click(screen.getByRole("button", { name: "Copier" }));
    expect(onCopy).toHaveBeenCalledWith("J'ai construit un pipeline SQL.!");
    expect(await screen.findByText("Brouillon copié.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Brouillon copié.");
  });

  it("says when the copy failed", async () => {
    const { user } = setup(DRAFT, vi.fn().mockRejectedValue(new Error("denied")));
    await user.click(screen.getByRole("button", { name: "Copier" }));
    expect(await screen.findByText(/Copie impossible/)).toBeInTheDocument();
  });

  it("keeps the focus on « Enregistrer » while it is busy (aria-disabled, never disabled)", async () => {
    const { user, onSave } = setup();
    await user.type(screen.getByLabelText("Post LinkedIn"), "!");
    const save = screen.getByRole("button", { name: "Enregistrer" });
    await user.click(save);
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(save).toHaveFocus();
    expect(save).not.toBeDisabled();
  });

  it("says on the card that a blank text cannot be saved, and sends nothing", async () => {
    const { user, onSave } = setup();
    await user.clear(screen.getByLabelText("Post LinkedIn"));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Le brouillon est vide");
    expect(screen.getByLabelText("Post LinkedIn")).toHaveAttribute("aria-invalid", "true");
  });

  it("says on the card that a text of more than 3 000 characters cannot be saved", async () => {
    const { user, onSave } = setup();
    const area = screen.getByLabelText("Post LinkedIn");
    await user.clear(area);
    await user.click(area);
    await user.paste("a".repeat(3001));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("3000 caractères au plus");
  });

  it("shows the server's refusal on its own card", () => {
    render(<DraftCard draft={DRAFT} onSave={vi.fn()} onCopy={vi.fn()} error="Requête invalide." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Requête invalide.");
  });

  it("reminds that nothing is published by the application", () => {
    setup();
    expect(
      screen.getByText("Rien n'est publié par l'application : copie et publie toi-même."),
    ).toBeInTheDocument();
  });
});
