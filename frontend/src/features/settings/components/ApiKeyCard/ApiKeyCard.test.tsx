import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ApiKeyEntry } from "../viewTypes";
import { ApiKeyCard } from "./ApiKeyCard";

const entry: ApiKeyEntry = {
  provider: "anthropic",
  label: "Anthropic",
  source: "ui",
  last4: "1234",
  readable: true,
  last_test_ok: null,
};

const noop = () => undefined;

describe("ApiKeyCard", () => {
  it("n'affiche jamais la clé et vide le champ après enregistrement", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={onSave} onDelete={noop} onTest={noop} />,
    );
    await user.type(screen.getByLabelText(/clé/i), "sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(onSave).toHaveBeenCalledWith("sk-ant-secret-1234");
    expect(screen.getByLabelText(/clé/i)).toHaveValue("");
    expect(screen.getByText("•••• 1234")).toBeInTheDocument();
    expect(screen.queryByText(/sk-ant/)).not.toBeInTheDocument();
  });

  it("garde la saisie quand l'enregistrement échoue, la vide quand il réussit", async () => {
    const user = userEvent.setup();
    const onSave = vi
      .fn()
      .mockRejectedValueOnce(new Error("refus"))
      .mockResolvedValueOnce(undefined);
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={onSave} onDelete={noop} onTest={noop} />,
    );
    await user.type(screen.getByLabelText(/clé/i), "sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(screen.getByLabelText(/clé/i)).toHaveValue("sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(screen.getByLabelText(/clé/i)).toHaveValue("");
  });

  it("a un champ mot de passe, sans saisie automatique, jamais prérempli", () => {
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={noop} onTest={noop} />,
    );
    const input = screen.getByLabelText(/clé/i);
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "off");
    expect(input).toHaveValue("");
  });

  it("désactive Enregistrer tant que le champ est vide", () => {
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={noop} onTest={noop} />,
    );
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
  });

  it("signale une clé illisible", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, readable: false }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("Clé illisible, ressaisis-la")).toBeInTheDocument();
  });

  it("indique l'origine « saisie ici » et propose la suppression", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={onDelete} onTest={noop} />,
    );
    expect(screen.getByText("saisie ici")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Supprimer" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("indique l'origine « fichier .env » et masque la suppression", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, source: "env" }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("fichier .env")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
    expect(screen.getByText(/retire-la de ce fichier/)).toBeInTheDocument();
  });

  it("annonce l'absence de clé et désactive le test", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, source: null, last4: null }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("Aucune clé enregistrée")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tester" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
  });

  it("lance le test et annonce le résultat dans une zone status", async () => {
    const user = userEvent.setup();
    const onTest = vi.fn();
    const { rerender } = render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={noop} onTest={onTest} />,
    );
    await user.click(screen.getByRole("button", { name: "Tester" }));
    expect(onTest).toHaveBeenCalledTimes(1);
    rerender(
      <ApiKeyCard
        entry={entry}
        testResult={{ ok: true, message: "Clé valide." }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={onTest}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Clé valide.");
  });

  it("désactive les boutons pendant une opération", () => {
    render(<ApiKeyCard entry={entry} pending onSave={noop} onDelete={noop} onTest={noop} />);
    expect(screen.getByRole("button", { name: "Tester" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Supprimer" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
  });

  it("rappelle le dernier test mémorisé par le serveur", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, last_test_ok: false }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("Dernier test : échoué")).toBeInTheDocument();
  });
});
