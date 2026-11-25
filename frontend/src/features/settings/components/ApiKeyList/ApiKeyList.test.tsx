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
  it("shows one card per provider", () => {
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProviders={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByLabelText("OpenAI API key")).toBeInTheDocument();
  });

  it("shows the test result and pending state on the matching card", () => {
    const onTest = vi.fn();
    render(
      <ApiKeyList
        entries={entries}
        testResults={{ anthropic: { ok: true, message: "Clé valide." } }}
        pendingProviders={["anthropic"]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={onTest}
      />,
    );
    const anthropic = within(screen.getByRole("article", { name: "Anthropic" }));
    expect(anthropic.getByRole("status")).toHaveTextContent("Clé valide.");
    expect(anthropic.getByRole("button", { name: "Test" })).toBeDisabled();
    expect(onTest).not.toHaveBeenCalled();
  });

  it("tests the selected provider", async () => {
    const user = userEvent.setup();
    const onTest = vi.fn();
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProviders={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={onTest}
      />,
    );
    const anthropic = within(screen.getByRole("article", { name: "Anthropic" }));
    await user.click(anthropic.getByRole("button", { name: "Test" }));
    expect(onTest).toHaveBeenCalledWith("anthropic");
  });

  it("saves the key for the selected provider", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProviders={[]}
        onSave={onSave}
        onDelete={vi.fn()}
        onTest={vi.fn()}
      />,
    );
    await user.type(screen.getByLabelText("OpenAI API key"), "sk-openai-9999");
    const openai = within(screen.getByRole("article", { name: "OpenAI" }));
    await user.click(openai.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith("openai", "sk-openai-9999");
  });

  it("marks several providers busy at once", () => {
    render(
      <ApiKeyList
        entries={entries}
        testResults={{}}
        pendingProviders={["anthropic", "openai"]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={vi.fn()}
      />,
    );
    const anthropic = within(screen.getByRole("article", { name: "Anthropic" }));
    expect(anthropic.getByRole("button", { name: "Test" })).toBeDisabled();
    expect(anthropic.getByRole("button", { name: "Delete" })).toBeDisabled();
  });
});
