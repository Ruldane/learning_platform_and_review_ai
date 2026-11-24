import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProviderOption } from "../viewTypes";
import { TierModelSelect } from "./TierModelSelect";

const anthropic: ProviderOption = {
  name: "anthropic",
  label: "Anthropic",
  has_key: true,
  models: ["claude-haiku-5-5", "claude-sonnet-5-5"],
};
const glm: ProviderOption = { name: "glm", label: "GLM (Z.ai)", has_key: true, models: null };
const openai: ProviderOption = {
  name: "openai",
  label: "OpenAI",
  has_key: false,
  models: ["gpt-6-luna", "gpt-6.1-sol"],
};

const STRONG_MODEL = "Model (Strong)";
const STRONG_PROVIDER = "Provider (Strong)";

describe("TierModelSelect", () => {
  it("uses a text field when the provider has no model list", () => {
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "glm", model: "x" }}
        providers={[glm]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("textbox", { name: STRONG_MODEL })).toHaveValue("x");
  });

  it("shows the provider's model list when available", () => {
    render(
      <TierModelSelect
        tier="rapide"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic, glm]}
        onChange={vi.fn()}
      />,
    );
    const select = screen.getByRole("combobox", { name: "Model (Fast)" });
    expect(select).toHaveValue("claude-haiku-5-5");
    expect(screen.getByRole("option", { name: "claude-sonnet-5-5" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("keeps the current model visible if it is missing from the list", () => {
    render(
      <TierModelSelect
        tier="rapide"
        value={{ provider: "anthropic", model: "claude-ancien" }}
        providers={[anthropic]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Model (Fast)" })).toHaveValue("claude-ancien");
  });

  it("labels a provider with no key and keeps it selectable", () => {
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic, openai]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("option", { name: "OpenAI (no key)" })).toBeEnabled();
    expect(screen.getByRole("option", { name: "Anthropic" })).toBeInTheDocument();
  });

  it("selects the first model when the provider changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-sonnet-5-5" }}
        providers={[anthropic, openai]}
        onChange={onChange}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox", { name: STRONG_PROVIDER }), "openai");
    expect(onChange).toHaveBeenCalledWith({ provider: "openai", model: "gpt-6-luna" });
  });

  it("reports a model selected from the list", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic]}
        onChange={onChange}
      />,
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: STRONG_MODEL }),
      "claude-sonnet-5-5",
    );
    expect(onChange).toHaveBeenCalledWith({ provider: "anthropic", model: "claude-sonnet-5-5" });
  });

  it("waits for a model name after switching to a provider with free text", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-sonnet-5-5" }}
        providers={[anthropic, glm]}
        onChange={onChange}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox", { name: STRONG_PROVIDER }), "glm");
    const input = screen.getByRole("textbox", { name: STRONG_MODEL });
    expect(input).toHaveValue("");
    expect(onChange).not.toHaveBeenCalled();
    await user.type(input, "glm-5.3");
    expect(onChange).not.toHaveBeenCalled();
    await user.tab();
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ provider: "glm", model: "glm-5.3" });
  });

  it("saves a typed model on Enter, once per change", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "glm", model: "x" }}
        providers={[glm]}
        onChange={onChange}
      />,
    );
    const input = screen.getByRole("textbox", { name: STRONG_MODEL });
    await user.type(input, "y{Enter}");
    expect(onChange).toHaveBeenCalledWith({ provider: "glm", model: "xy" });
    await user.tab();
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("skips onChange if the typed model is unchanged", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "glm", model: "x" }}
        providers={[glm]}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("textbox", { name: STRONG_MODEL }));
    await user.tab();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("disables the fields while saving", () => {
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic]}
        disabled
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: STRONG_PROVIDER })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: STRONG_MODEL })).toBeDisabled();
  });
});
