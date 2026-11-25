import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CallFilters } from "./CallFilters";

describe("CallFilters", () => {
  it('reports an agent, a flow, and null for "All"', async () => {
    const onAgentChange = vi.fn();
    const onGraphChange = vi.fn();
    render(
      <CallFilters
        agent="scribe"
        graph={null}
        onAgentChange={onAgentChange}
        onGraphChange={onGraphChange}
      />,
    );
    const agent = screen.getByLabelText("Agent");
    expect(agent).toHaveValue("scribe");
    expect(screen.getByLabelText("Flow")).toHaveValue("");
    await userEvent.selectOptions(agent, "");
    expect(onAgentChange).toHaveBeenCalledWith(null);
    await userEvent.selectOptions(screen.getByLabelText("Flow"), "quiz");
    expect(onGraphChange).toHaveBeenCalledWith("quiz");
  });

  it("names agents and flows in English", () => {
    render(
      <CallFilters agent={null} graph={null} onAgentChange={vi.fn()} onGraphChange={vi.fn()} />,
    );
    expect(
      within(screen.getByLabelText("Agent")).getByRole("option", { name: "Scribe" }),
    ).toHaveValue("scribe");
    expect(
      within(screen.getByLabelText("Flow")).getByRole("option", { name: "Morning brief" }),
    ).toHaveValue("daily_brief");
  });
});
