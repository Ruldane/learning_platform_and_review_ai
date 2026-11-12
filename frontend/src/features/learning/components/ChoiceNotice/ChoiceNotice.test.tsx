import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChoiceNotice } from "./ChoiceNotice";

describe("ChoiceNotice", () => {
  it("shows the question and leads to the proposals, with no free text field", async () => {
    const user = userEvent.setup();
    const onShowProposals = vi.fn();
    render(
      <ChoiceNotice
        question="Choisis un parcours."
        answered={false}
        onShowProposals={onShowProposals}
      />,
    );
    expect(screen.getByText("Choisis un parcours.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Voir les propositions" }));
    expect(onShowProposals).toHaveBeenCalledTimes(1);
  });

  it("says the answer was sent once answered", () => {
    render(<ChoiceNotice question="Choisis." answered onShowProposals={vi.fn()} />);
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
