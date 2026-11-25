import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeVotes } from "../fixtures";
import { VotesPanel } from "./VotesPanel";

describe("VotesPanel", () => {
  it("shows the four votes in the committee order, each with its persona and its objection", () => {
    render(<VotesPanel votes={makeVotes()} />);
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("heading").textContent)).toEqual([
      expect.stringContaining("ATS reader"),
      expect.stringContaining("Recruiter"),
      expect.stringContaining("Manager"),
      expect.stringContaining("Future colleague"),
    ]);
    const manager = within(items[2]!);
    expect(manager.getByText("No")).toBeVisible();
    expect(manager.getByText("Main objection")).toBeVisible();
    expect(manager.getByText("Peu de résultats chiffrés.")).toBeVisible();
    expect(manager.getByText("Reason")).toBeVisible();
  });

  it("writes every vote in words: yes, no, maybe", () => {
    const votes = makeVotes().map((vote, index) => ({
      ...vote,
      vote: (["yes", "no", "maybe", "yes"] as const)[index]!,
    }));
    render(<VotesPanel votes={votes} />);
    const items = screen.getAllByRole("listitem");
    expect(within(items[0]!).getByText("Yes")).toBeVisible();
    expect(within(items[1]!).getByText("No")).toBeVisible();
    expect(within(items[2]!).getByText("Maybe")).toBeVisible();
  });
});
