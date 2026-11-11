import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { FormEvent } from "react";
import { describe, expect, it, vi } from "vitest";
import { DomainListEditor } from "./DomainListEditor";

const LABEL = "Domaines privilégiés";
const FIELD = "Ajouter un domaine";

describe("DomainListEditor", () => {
  it("normalise la saisie puis ajoute le domaine", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainListEditor label={LABEL} value={[]} onChange={onChange} />);
    await user.type(screen.getByLabelText(FIELD), "https://www.Python.org/doc{Enter}");
    expect(onChange).toHaveBeenLastCalledWith(["python.org"]);
    expect(screen.getByLabelText(FIELD)).toHaveValue("");
  });

  it("ajoute aussi par le bouton", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainListEditor label={LABEL} value={["a.org"]} onChange={onChange} />);
    await user.type(screen.getByLabelText(FIELD), "b.org");
    await user.click(screen.getByRole("button", { name: "Ajouter" }));
    expect(onChange).toHaveBeenLastCalledWith(["a.org", "b.org"]);
  });

  it("refuse un doublon, même écrit autrement, avec un message en ligne", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainListEditor label={LABEL} value={["python.org"]} onChange={onChange} />);
    await user.type(screen.getByLabelText(FIELD), "WWW.python.org{Enter}");
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Ce domaine est déjà dans la liste.");
    expect(screen.getByLabelText(FIELD)).toHaveAttribute("aria-invalid", "true");
  });

  it("refuse un domaine invalide, puis efface le message à la frappe", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainListEditor label={LABEL} value={[]} onChange={onChange} />);
    await user.type(screen.getByLabelText(FIELD), "pas un domaine{Enter}");
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Ce domaine n'est pas valide.");
    await user.type(screen.getByLabelText(FIELD), "x");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("n'ajoute rien quand le champ est vide", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainListEditor label={LABEL} value={[]} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Ajouter" }));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("retire un domaine par son bouton", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainListEditor label={LABEL} value={["a.org", "b.org"]} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Retirer a.org" }));
    expect(onChange).toHaveBeenCalledWith(["b.org"]);
  });

  it("refuse un ajout au-delà du maximum", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <DomainListEditor label={LABEL} value={["a.org", "b.org"]} max={2} onChange={onChange} />,
    );
    await user.type(screen.getByLabelText(FIELD), "c.org{Enter}");
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "La liste est pleine (2 domaines au plus).",
    );
  });

  it("nomme le groupe et dit quand la liste est vide", () => {
    render(<DomainListEditor label={LABEL} value={[]} onChange={vi.fn()} />);
    expect(screen.getByRole("group", { name: LABEL })).toBeInTheDocument();
    expect(screen.getByText("Aucun domaine.")).toBeInTheDocument();
  });

  it("n'envoie pas un formulaire parent à Entrée", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn((event: FormEvent) => event.preventDefault());
    render(
      <form onSubmit={onSubmit}>
        <DomainListEditor label={LABEL} value={[]} onChange={vi.fn()} />
      </form>,
    );
    await user.type(screen.getByLabelText(FIELD), "a.org{Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
