import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CancelCouncilCard } from "./CancelCouncilCard";

describe("CancelCouncilCard", () => {
  it("confirms or keeps, without any browser dialog", async () => {
    const user = userEvent.setup();
    const confirmDialog = vi.spyOn(window, "confirm");
    const onConfirm = vi.fn();
    const onKeep = vi.fn();
    render(<CancelCouncilCard disabled={false} onConfirm={onConfirm} onKeep={onKeep} />);
    await user.click(screen.getByRole("button", { name: "Non, continuer" }));
    expect(onKeep).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Oui, arrêter" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(confirmDialog).not.toHaveBeenCalled();
  });

  it("locks the confirmation while the cancellation is sent", () => {
    render(<CancelCouncilCard disabled onConfirm={vi.fn()} onKeep={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Oui, arrêter" })).toBeDisabled();
  });
});
