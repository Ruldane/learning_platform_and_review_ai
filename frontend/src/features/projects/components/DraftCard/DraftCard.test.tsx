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
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText("Post LinkedIn"), " Merci !");
    expect(save).toBeEnabled();
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
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
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

  it("reminds that nothing is published by the application", () => {
    setup();
    expect(
      screen.getByText("Rien n'est publié par l'application : copie et publie toi-même."),
    ).toBeInTheDocument();
  });
});
