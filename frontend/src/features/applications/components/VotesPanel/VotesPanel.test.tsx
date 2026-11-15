import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeVotes } from "../fixtures";
import { VotesPanel } from "./VotesPanel";

describe("VotesPanel", () => {
  it("shows the four votes in the committee order, each with its persona and its objection", () => {
    render(<VotesPanel votes={makeVotes()} />);
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("heading").textContent)).toEqual([
      expect.stringContaining("Lecteur ATS"),
      expect.stringContaining("Recruteur"),
      expect.stringContaining("Manager"),
      expect.stringContaining("Futur collègue"),
    ]);
    const manager = within(items[2]!);
    expect(manager.getByText("Non")).toBeVisible();
    expect(manager.getByText("Objection principale")).toBeVisible();
    expect(manager.getByText("Peu de résultats chiffrés.")).toBeVisible();
    expect(manager.getByText("Raison")).toBeVisible();
  });

  it("writes every vote in words: yes, no, maybe", () => {
    const votes = makeVotes().map((vote, index) => ({
      ...vote,
      vote: (["oui", "non", "peut_etre", "oui"] as const)[index]!,
    }));
    render(<VotesPanel votes={votes} />);
    const items = screen.getAllByRole("listitem");
    expect(within(items[0]!).getByText("Oui")).toBeVisible();
    expect(within(items[1]!).getByText("Non")).toBeVisible();
    expect(within(items[2]!).getByText("Peut-être")).toBeVisible();
  });
});
