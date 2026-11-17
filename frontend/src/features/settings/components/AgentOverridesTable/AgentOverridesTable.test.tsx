import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AgentOverrides, ProviderOption, TierChoices } from "../viewTypes";
import { AgentOverridesTable } from "./AgentOverridesTable";

const providers: ProviderOption[] = [
  { name: "openai", label: "OpenAI", has_key: true, models: ["gpt-6-luna"] },
];
const haiku = { provider: "anthropic", model: "claude-haiku-5-5" };
const tiers: TierChoices = { rapide: haiku, standard: haiku, fort: haiku, vision: haiku };
const agents = [
  { name: "scout", tier: "rapide" as const },
  { name: "tutor", tier: "standard" as const },
  { name: "ghost_agent", tier: null },
];

function table(
  over: { overrides?: AgentOverrides; disabled?: boolean; onChange?: () => void } = {},
) {
  return (
    <AgentOverridesTable
      agents={agents}
      overrides={over.overrides ?? {}}
      tiers={tiers}
      providers={providers}
      disabled={over.disabled}
      onChange={over.onChange ?? vi.fn()}
    />
  );
}

describe("AgentOverridesTable", () => {
  it("lists one agent per row with its tier and the model of that tier", () => {
    render(table({ overrides: { tutor: { provider: "openai", model: "gpt-6-luna" } } }));
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    expect(within(rows[0]!).getByRole("rowheader")).toHaveTextContent("Éclaireur");
    expect(within(rows[0]!).getByText("Rapide")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("anthropic : claude-haiku-5-5")).toBeInTheDocument();
    expect(screen.getByLabelText("Fournisseur (Tuteur)")).toHaveValue("openai");
    expect(screen.getByLabelText("Fournisseur (Éclaireur)")).toHaveValue("");
  });

  it("names an agent the server no longer knows by its raw name, with no tier", () => {
    render(table());
    const row = screen.getAllByRole("row")[3]!;
    expect(within(row).getByRole("rowheader")).toHaveTextContent("ghost_agent");
    expect(
      within(row).getByText("Agent inconnu : rends-le au niveau par défaut."),
    ).toBeInTheDocument();
    expect(within(row).getByText("Inconnu")).toBeInTheDocument();
    expect(within(row).getByRole("option", { name: "Niveau par défaut" })).toBeInTheDocument();
  });

  it("reports the agent and its choice, and is disabled while saving", async () => {
    const onChange = vi.fn();
    const { rerender } = render(table({ onChange }));
    await userEvent.setup().selectOptions(screen.getByLabelText("Fournisseur (Tuteur)"), "openai");
    expect(onChange).toHaveBeenCalledWith("tutor", { provider: "openai", model: "gpt-6-luna" });
    rerender(table({ onChange, disabled: true }));
    expect(screen.getByLabelText("Fournisseur (Tuteur)")).toBeDisabled();
  });
});
