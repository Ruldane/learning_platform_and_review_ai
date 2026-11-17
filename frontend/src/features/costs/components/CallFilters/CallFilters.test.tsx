import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CallFilters } from "./CallFilters";

describe("CallFilters", () => {
  it("reports an agent, a graph, and `null` for « Tous »", async () => {
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
    expect(screen.getByLabelText("Parcours")).toHaveValue("");
    await userEvent.selectOptions(agent, "");
    expect(onAgentChange).toHaveBeenCalledWith(null);
    await userEvent.selectOptions(screen.getByLabelText("Parcours"), "quiz");
    expect(onGraphChange).toHaveBeenCalledWith("quiz");
  });

  it("names agents and graphs in French", () => {
    render(
      <CallFilters agent={null} graph={null} onAgentChange={vi.fn()} onGraphChange={vi.fn()} />,
    );
    expect(
      within(screen.getByLabelText("Agent")).getByRole("option", { name: "Scribe" }),
    ).toHaveValue("scribe");
    expect(
      within(screen.getByLabelText("Parcours")).getByRole("option", { name: "Brief du matin" }),
    ).toHaveValue("daily_brief");
  });
});
