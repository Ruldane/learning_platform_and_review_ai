import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { makeProposals } from "./fixtures";
import { ProposalCards } from "./ProposalCards";

function setup(over: Partial<ComponentProps<typeof ProposalCards>> = {}) {
  const handlers = {
    onChoose: vi.fn(),
    onMix: vi.fn(),
    onAnotherRound: vi.fn(),
    onShowBoard: vi.fn(),
  };
  render(
    <ProposalCards proposals={makeProposals()} canChoose busy={false} {...handlers} {...over} />,
  );
  return { user: userEvent.setup(), ...handlers };
}

const tick = (name: string) => ({ name: `Mélanger « ${name} »` });

describe("ProposalCards", () => {
  it("lists twice the same item without mixing the rows (no duplicate key)", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const [first, ...others] = makeProposals();
    setup({ proposals: [{ ...first!, skills: ["Python", "Python"] }, ...others] });
    const card = screen.getAllByRole("article")[0]!;
    expect(within(card).getAllByText("Python")).toHaveLength(2);
    expect(JSON.stringify(error.mock.calls)).not.toContain("same key");
    error.mockRestore();
  });

  it("shows the same sections on every card", () => {
    setup();
    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(3);
    for (const card of cards) {
      for (const heading of [
        "Durée",
        "Charge",
        "Compétences couvertes",
        "Projet final",
        "Compromis",
      ]) {
        expect(within(card).getByText(heading)).toBeInTheDocument();
      }
    }
  });

  it("describes a proposal", () => {
    setup();
    const card = screen.getByRole("article", { name: "Le parcours solide" });
    expect(within(card).getByText("16 weeks")).toBeInTheDocument();
    expect(within(card).getByText("7.5 h per week")).toBeInTheDocument();
    expect(within(card).getByText("Statistiques")).toBeInTheDocument();
    expect(within(card).getByText("Long")).toBeInTheDocument();
    expect(
      within(card).getByText("Une application complète avec sa base de données"),
    ).toBeInTheDocument();
    const one = screen.getByRole("article", { name: "Le parcours projet" });
    expect(within(one).getByText("1 week")).toBeInTheDocument();
  });

  it("orders the cards by rank", () => {
    setup({ proposals: makeProposals().reverse() });
    expect(screen.getAllByRole("article").map((a) => a.getAttribute("aria-label"))).toEqual([
      "Le parcours express",
      "Le parcours solide",
      "Le parcours projet",
    ]);
  });

  it("chooses one proposal", async () => {
    const { user, onChoose } = setup();
    await user.click(screen.getByRole("button", { name: "Choose “Le parcours solide”" }));
    expect(onChoose).toHaveBeenCalledWith("p2");
  });

  it("marks the chosen proposal and cannot choose it again", () => {
    const proposals = makeProposals().map((p) => ({ ...p, chosen: p.id === "p1" }));
    setup({ proposals, canChoose: false });
    const card = screen.getByRole("article", { name: "Le parcours express" });
    expect(within(card).getByText("Path chosen")).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /^Choose/ })).toBeNull();
  });

  it("mixes exactly two proposals", async () => {
    const { user, onMix } = setup();
    const mix = screen.getByRole("button", { name: "Mix these two paths" });
    expect(mix).toBeDisabled();
    await user.click(screen.getByRole("checkbox", tick("Le parcours projet")));
    expect(mix).toBeDisabled();
    await user.click(screen.getByRole("checkbox", tick("Le parcours express")));
    expect(mix).toBeEnabled();
    await user.click(mix);
    // Dans l'ordre des cartes, pas dans l'ordre des clics.
    expect(onMix).toHaveBeenCalledWith("p1", "p3");
  });

  it("mixes p1 and p2", async () => {
    const { user, onMix } = setup();
    await user.click(screen.getByRole("checkbox", tick("Le parcours express")));
    await user.click(screen.getByRole("checkbox", tick("Le parcours solide")));
    await user.click(screen.getByRole("button", { name: "Mix these two paths" }));
    expect(onMix).toHaveBeenCalledWith("p1", "p2");
  });

  it("does not let a third card be ticked", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("checkbox", tick("Le parcours express")));
    await user.click(screen.getByRole("checkbox", tick("Le parcours solide")));
    expect(screen.getByRole("checkbox", tick("Le parcours projet"))).toBeDisabled();
    await user.click(screen.getByRole("checkbox", tick("Le parcours solide")));
    expect(screen.getByRole("checkbox", tick("Le parcours projet"))).toBeEnabled();
  });

  it("says how many cards are ticked", async () => {
    const { user } = setup();
    expect(
      screen.getByText("Check two proposals to mix them (0 / 2)."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", tick("Le parcours express")));
    expect(
      screen.getByText("Check two proposals to mix them (1 / 2)."),
    ).toBeInTheDocument();
  });

  it("asks for another round", async () => {
    const { user, onAnotherRound } = setup();
    await user.click(screen.getByRole("button", { name: "Ask for another round" }));
    expect(onAnotherRound).toHaveBeenCalledTimes(1);
  });

  it("offers no other round when the interrupt does not (round cap)", () => {
    setup({ canAnotherRound: false });
    expect(screen.queryByRole("button", { name: "Ask for another round" })).toBeNull();
    expect(screen.getByRole("button", { name: "Mix these two paths" })).toBeInTheDocument();
  });

  it("drops the mix bar once a parcours is chosen", () => {
    const proposals = makeProposals().map((p) => ({ ...p, chosen: p.id === "p1" }));
    setup({ proposals, canChoose: false });
    expect(screen.queryByRole("button", { name: "Mix these two paths" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ask for another round" })).toBeNull();
    expect(screen.queryByText(/You can choose/)).toBeNull();
  });

  it("shows a proposal on the board, only when it has one", async () => {
    const { user, onShowBoard } = setup();
    expect(screen.getAllByRole("button", { name: /on the board/ })).toHaveLength(2);
    await user.click(
      screen.getByRole("button", { name: "Show “Le parcours express” on the board" }),
    );
    expect(onShowBoard).toHaveBeenCalledWith("b1");
  });

  it("disables the actions when canChoose is false", async () => {
    const { user, onChoose, onMix, onAnotherRound } = setup({ canChoose: false });
    for (const button of screen.getAllByRole("button", { name: /^Choose/ })) {
      expect(button).toBeDisabled();
    }
    for (const box of screen.getAllByRole("checkbox")) expect(box).toBeDisabled();
    expect(screen.getByRole("button", { name: "Mix these two paths" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Ask for another round" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Choose “Le parcours express”" }));
    expect(onChoose).not.toHaveBeenCalled();
    expect(onMix).not.toHaveBeenCalled();
    expect(onAnotherRound).not.toHaveBeenCalled();
    expect(
      screen.getByText("You can choose once the team has finished its debate."),
    ).toBeInTheDocument();
  });

  it("keeps reading the board while an action is running", () => {
    setup({ busy: true });
    for (const button of screen.getAllByRole("button", { name: /^Choose/ })) {
      expect(button).toBeDisabled();
    }
    expect(
      screen.getByRole("button", { name: "Show “Le parcours express” on the board" }),
    ).toBeEnabled();
  });

  it("forgets a ticked card that is no longer proposed", async () => {
    const user = userEvent.setup();
    const props = { canChoose: true, busy: false, onChoose: vi.fn(), onMix: vi.fn() };
    const handlers = { onAnotherRound: vi.fn(), onShowBoard: vi.fn() };
    const { rerender } = render(
      <ProposalCards proposals={makeProposals()} {...props} {...handlers} />,
    );
    await user.click(screen.getByRole("checkbox", tick("Le parcours express")));
    await user.click(screen.getByRole("checkbox", tick("Le parcours solide")));
    expect(screen.getByRole("button", { name: "Mix these two paths" })).toBeEnabled();
    rerender(
      <ProposalCards
        proposals={makeProposals().filter((p) => p.id !== "p1")}
        {...props}
        {...handlers}
      />,
    );
    expect(screen.getByRole("button", { name: "Mix these two paths" })).toBeDisabled();
  });

  it("explains that nothing is proposed yet", () => {
    setup({ proposals: [] });
    expect(screen.getByText(/No proposals yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("never opens a blocking browser dialog", async () => {
    const confirm = vi.spyOn(window, "confirm");
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: "Choose “Le parcours express”" }));
    expect(confirm).not.toHaveBeenCalled();
    confirm.mockRestore();
  });
});
