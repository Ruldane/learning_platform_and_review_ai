import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProviderOption, TierChoices } from "../viewTypes";
import { TierModelTable } from "./TierModelTable";

const providers: ProviderOption[] = [
  {
    name: "anthropic",
    label: "Anthropic",
    has_key: true,
    models: ["claude-haiku-5-5", "claude-sonnet-5-5"],
  },
];
const choice = { provider: "anthropic", model: "claude-haiku-5-5" };
const tiers: TierChoices = { fast: choice, standard: choice, strong: choice, vision: choice };

describe("TierModelTable", () => {
  it("shows the four tiers and their uses", () => {
    render(<TierModelTable tiers={tiers} providers={providers} onChange={vi.fn()} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);
    expect(within(rows[0]!).getByText("Fast")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("Search, extraction, moderation")).toBeInTheDocument();
    expect(screen.getByText("Debate, proofreading, quizzes, tutoring")).toBeInTheDocument();
    expect(screen.getByText("Planning, lesson writing, interviews")).toBeInTheDocument();
    expect(screen.getByText("CV design capture")).toBeInTheDocument();
  });

  it("reports the changed tier and its new model", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TierModelTable tiers={tiers} providers={providers} onChange={onChange} />);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Model (Strong)" }),
      "claude-sonnet-5-5",
    );
    expect(onChange).toHaveBeenCalledWith("strong", {
      provider: "anthropic",
      model: "claude-sonnet-5-5",
    });
  });

  it("disables the selectors while saving", () => {
    render(<TierModelTable tiers={tiers} providers={providers} disabled onChange={vi.fn()} />);
    for (const select of screen.getAllByRole("combobox")) expect(select).toBeDisabled();
  });
});
