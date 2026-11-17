import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClaimChoice } from "./ClaimChoice";

const TAKE = "Reprendre les données de cet ordinateur";

describe("ClaimChoice", () => {
  it("sends the choice of each button", async () => {
    const user = userEvent.setup();
    const onChoose = vi.fn();
    render(<ClaimChoice onChoose={onChoose} pending={false} />);
    await user.click(screen.getByRole("button", { name: TAKE }));
    await user.click(screen.getByRole("button", { name: "Commencer un espace vide" }));
    expect(onChoose.mock.calls).toEqual([["take_local"], ["fresh"]]);
  });

  it("ignores clicks while sending, without taking the focus away from the button", async () => {
    const user = userEvent.setup();
    const onChoose = vi.fn();
    render(<ClaimChoice onChoose={onChoose} pending />);
    const take = screen.getByRole("button", { name: TAKE });
    take.focus();
    await user.keyboard("{Enter}");
    expect(onChoose).not.toHaveBeenCalled();
    expect(take).toHaveFocus();
    expect(take).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("status")).toHaveTextContent("Un instant");
  });

  it("shows an error under the buttons", () => {
    render(<ClaimChoice onChoose={vi.fn()} pending={false} error="Pas possible." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Pas possible.");
  });
});
