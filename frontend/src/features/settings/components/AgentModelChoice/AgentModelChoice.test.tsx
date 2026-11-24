import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProviderOption } from "../viewTypes";
import { AgentModelChoice } from "./AgentModelChoice";

const providers: ProviderOption[] = [
  { name: "openai", label: "OpenAI", has_key: true, models: ["gpt-6-luna", "gpt-6.1-sol"] },
  { name: "glm", label: "GLM", has_key: false, models: null },
];
const DEFAULT_TIER = "Default tier (Standard)";
const PROVIDER = "Provider (Tutor)";
const MODEL = "Model (Tutor)";
const base = { agentName: "Tutor", defaultLabel: DEFAULT_TIER, providers };
const choice = { provider: "openai", model: "gpt-6-luna" };

describe("AgentModelChoice", () => {
  it("offers the default tier first, with no model field while on it", () => {
    render(<AgentModelChoice {...base} value={undefined} onChange={vi.fn()} />);
    expect(screen.getByLabelText(PROVIDER)).toHaveValue("");
    expect(screen.getAllByRole("option")[0]).toHaveTextContent(DEFAULT_TIER);
    expect(screen.queryByLabelText(MODEL)).not.toBeInTheDocument();
  });

  it("picks the first model of a provider that has a list", async () => {
    const onChange = vi.fn();
    render(<AgentModelChoice {...base} value={undefined} onChange={onChange} />);
    await userEvent.setup().selectOptions(screen.getByLabelText(PROVIDER), "openai");
    expect(onChange).toHaveBeenCalledWith(choice);
  });

  it("goes back to the tier with null, but says nothing when it already follows it", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<AgentModelChoice {...base} value={choice} onChange={onChange} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(PROVIDER), "");
    expect(onChange).toHaveBeenCalledWith(null);
    onChange.mockClear();
    rerender(<AgentModelChoice {...base} value={undefined} onChange={onChange} />);
    await user.selectOptions(screen.getByLabelText(PROVIDER), "");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("waits for a typed model with a provider that has no list, and trims it", async () => {
    const onChange = vi.fn();
    render(<AgentModelChoice {...base} value={undefined} onChange={onChange} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(PROVIDER), "glm");
    expect(onChange).not.toHaveBeenCalled();
    // rien n'est envoyé encore : le champ le dit
    expect(screen.getByLabelText(MODEL)).toHaveAccessibleDescription(
      "Type the model, then press Enter.",
    );
    await user.type(screen.getByLabelText(MODEL), "  glm-5.3 {Enter}");
    expect(onChange).toHaveBeenCalledExactlyOnceWith({ provider: "glm", model: "glm-5.3" });
  });

  it("drops the waiting provider when the saved choice changes", async () => {
    const { rerender } = render(
      <AgentModelChoice {...base} value={undefined} onChange={vi.fn()} />,
    );
    await userEvent.setup().selectOptions(screen.getByLabelText(PROVIDER), "glm");
    rerender(<AgentModelChoice {...base} value={choice} onChange={vi.fn()} />);
    expect(screen.getByLabelText(PROVIDER)).toHaveValue("openai");
  });
});
