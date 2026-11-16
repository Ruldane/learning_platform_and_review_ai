import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProfileEntryView } from "../viewTypes";
import { ProfileEntryForm } from "./ProfileEntryForm";

const ENTRY: ProfileEntryView = {
  name: "Pipeline de ventes",
  description: "Agrégation mensuelle des ventes.",
  achievements: ["Requêtes SQL optimisées", "Tests du total"],
};

function setup(entry = ENTRY, added = false) {
  const onAdd = vi.fn();
  render(<ProfileEntryForm entry={entry} added={added} onAdd={onAdd} />);
  return { onAdd, user: userEvent.setup() };
}

const add = () => screen.getByRole("button", { name: "Ajouter au profil maître" });

describe("ProfileEntryForm", () => {
  it("proposes the entry and reminds that nothing enters the profile without consent", () => {
    setup();
    expect(screen.getByLabelText("Nom du projet")).toHaveValue("Pipeline de ventes");
    expect(screen.getByLabelText("Réalisations")).toHaveValue(
      "Requêtes SQL optimisées\nTests du total",
    );
    expect(screen.getByText("Rien n'entre dans ton profil sans ton accord.")).toBeInTheDocument();
  });

  it("adds the entry only on the click, never on its own", async () => {
    const { onAdd, user } = setup();
    expect(onAdd).not.toHaveBeenCalled();
    await user.click(add());
    expect(onAdd).toHaveBeenCalledWith(ENTRY);
  });

  it("drops empty and blank achievement lines and trims the name and the description", async () => {
    const { onAdd, user } = setup({ name: "", description: "", achievements: [] });
    await user.type(screen.getByLabelText("Nom du projet"), "  Pipeline  ");
    await user.type(screen.getByLabelText("Description"), "  Une description.  ");
    await user.type(
      screen.getByLabelText("Réalisations"),
      "Première{Enter}{Enter}   {Enter}  Deuxième  {Enter}\t",
    );
    await user.click(add());
    expect(onAdd).toHaveBeenCalledWith({
      name: "Pipeline",
      description: "Une description.",
      achievements: ["Première", "Deuxième"],
    });
  });

  it("refuses a blank name with a field error and adds nothing", async () => {
    const { onAdd, user } = setup({ ...ENTRY, name: "   " });
    await user.click(add());
    expect(onAdd).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Donne un nom au projet");
    expect(screen.getByLabelText("Nom du projet")).toBeInvalid();
  });

  it("refuses more than four achievements, once blank lines are dropped", async () => {
    const { onAdd, user } = setup({
      ...ENTRY,
      achievements: ["a", "", "b", "c", "  ", "d", "e"],
    });
    await user.click(add());
    expect(onAdd).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("4 réalisations au plus.");
  });

  it("accepts four achievements even with blank lines between them", async () => {
    const { onAdd, user } = setup({ ...ENTRY, achievements: ["a", "", "b", "  ", "c", "d"] });
    await user.click(add());
    expect(onAdd).toHaveBeenCalledWith({ ...ENTRY, achievements: ["a", "b", "c", "d"] });
  });

  it("refuses a description over 600 characters and an achievement over 200", async () => {
    const { onAdd, user } = setup({
      name: "Projet",
      description: "d".repeat(601),
      achievements: ["r".repeat(201)],
    });
    await user.click(add());
    expect(onAdd).not.toHaveBeenCalled();
    const alerts = screen.getAllByRole("alert").map((a) => a.textContent);
    expect(alerts).toContain("La description fait 600 caractères au plus.");
    expect(alerts).toContain("Chaque réalisation fait 200 caractères au plus.");
  });

  it("replaces the button by « Ajouté au profil (version N) » once added, and locks the form", async () => {
    const onAdd = vi.fn();
    render(<ProfileEntryForm entry={ENTRY} added version={4} onAdd={onAdd} />);
    expect(screen.getByRole("status")).toHaveTextContent("Ajouté au profil (version 4)");
    expect(screen.queryByRole("button", { name: "Ajouter au profil maître" })).toBeNull();
    expect(screen.getByLabelText("Nom du projet")).toBeDisabled();
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("says the entry is in the profile when the version is unknown", () => {
    setup(ENTRY, true);
    expect(screen.getByRole("status")).toHaveTextContent("Ajouté au profil maître.");
    expect(screen.queryByRole("button", { name: "Ajouter au profil maître" })).toBeNull();
  });

  it("disables the button while the entry is being added", () => {
    render(<ProfileEntryForm entry={ENTRY} added={false} busy onAdd={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Ajout en cours…" })).toBeDisabled();
  });

  it("reads its entry once: a new entry comes with a new key", () => {
    const { rerender } = render(
      <ProfileEntryForm key="a" entry={ENTRY} added={false} onAdd={vi.fn()} />,
    );
    rerender(
      <ProfileEntryForm
        key="a"
        entry={{ ...ENTRY, name: "Autre" }}
        added={false}
        onAdd={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Nom du projet")).toHaveValue("Pipeline de ventes");
    rerender(
      <ProfileEntryForm
        key="b"
        entry={{ ...ENTRY, name: "Autre" }}
        added={false}
        onAdd={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Nom du projet")).toHaveValue("Autre");
  });
});
