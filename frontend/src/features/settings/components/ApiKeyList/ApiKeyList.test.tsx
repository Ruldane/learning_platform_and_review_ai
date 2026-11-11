import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ApiKeyEntry } from "../viewTypes";
import { ApiKeyList } from "./ApiKeyList";

const entries: ApiKeyEntry[] = [
  {
    provider: "anthropic",
    label: "Anthropic",
    source: "ui",
    last4: "1234",
    readable: true,
    last_test_ok: null,
  },
  {
    provider: "openai",
    label: "OpenAI",
    source: null,
    last4: null,
    readable: true,
    last_test_ok: null,
  },
];

describe("ApiKeyList", () => {
  it("affiche une carte par fournisseur", () => {
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProvider={null}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByLabelText("Clé API OpenAI")).toBeInTheDocument();
  });

  it("transmet le résultat du test et l'état en cours à la bonne carte", () => {
    const onTest = vi.fn();
    render(
      <ApiKeyList
        entries={entries}
        testResults={{ anthropic: { ok: true, message: "Clé valide." } }}
        pendingProvider="anthropic"
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={onTest}
      />,
    );
    const anthropic = within(screen.getByRole("article", { name: "Anthropic" }));
    expect(anthropic.getByRole("status")).toHaveTextContent("Clé valide.");
    expect(anthropic.getByRole("button", { name: "Tester" })).toBeDisabled();
    expect(onTest).not.toHaveBeenCalled();
  });

  it("lance le test du bon fournisseur", async () => {
    const user = userEvent.setup();
    const onTest = vi.fn();
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProvider={null}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={onTest}
      />,
    );
    const anthropic = within(screen.getByRole("article", { name: "Anthropic" }));
    await user.click(anthropic.getByRole("button", { name: "Tester" }));
    expect(onTest).toHaveBeenCalledWith("anthropic");
  });

  it("enregistre une clé pour le bon fournisseur", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProvider={null}
        onSave={onSave}
        onDelete={vi.fn()}
        onTest={vi.fn()}
      />,
    );
    await user.type(screen.getByLabelText("Clé API OpenAI"), "sk-openai-9999");
    const openai = within(screen.getByRole("article", { name: "OpenAI" }));
    await user.click(openai.getByRole("button", { name: "Enregistrer" }));
    expect(onSave).toHaveBeenCalledWith("openai", "sk-openai-9999");
  });
});
