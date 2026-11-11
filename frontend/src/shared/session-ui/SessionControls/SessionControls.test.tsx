import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import type { SessionStatus } from "@/shared/realtime/types";
import { SessionControls } from "./SessionControls";

function setup(status: SessionStatus, extra?: ReactNode) {
  const handlers = { onPause: vi.fn(), onResume: vi.fn(), onCancel: vi.fn() };
  render(<SessionControls status={status} {...handlers} extraActions={extra} />);
  return handlers;
}

describe("SessionControls", () => {
  it("shows Pause and Annuler while running", async () => {
    const user = userEvent.setup();
    const h = setup("running");
    expect(screen.queryByRole("button", { name: "Reprendre" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Pause" }));
    await user.click(screen.getByRole("button", { name: "Annuler" }));
    expect(h.onPause).toHaveBeenCalledOnce();
    expect(h.onCancel).toHaveBeenCalledOnce();
  });

  it("shows Reprendre when paused", async () => {
    const user = userEvent.setup();
    const h = setup("paused");
    expect(screen.queryByRole("button", { name: "Pause" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Reprendre" }));
    expect(h.onResume).toHaveBeenCalledOnce();
  });

  it("keeps Annuler while waiting for the user but offers no Pause", () => {
    setup("waiting_user");
    expect(screen.getByRole("button", { name: "Annuler" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).toBeNull();
  });

  it.each(["completed", "failed", "cancelled"] as const)("hides every control once %s", (s) => {
    setup(s);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders extra actions next to the controls", () => {
    setup("running", <button type="button">Plus concret</button>);
    expect(screen.getByRole("button", { name: "Plus concret" })).toBeInTheDocument();
  });
});
