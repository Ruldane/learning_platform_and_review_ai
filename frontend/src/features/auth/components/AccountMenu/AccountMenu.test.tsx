import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AccountMenu } from "./AccountMenu";

describe("AccountMenu", () => {
  it("shows the address and logs out on request", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    render(
      <AccountMenu
        email="camille.exemple@example.org"
        onLogout={onLogout}
        pending={false}
        failed={false}
      />,
    );
    const group = screen.getByRole("group", { name: "Account" });
    expect(group).toHaveTextContent("camille.exemple@example.org");
    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it("does not log out twice while sending, and says when it failed", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    const { rerender } = render(
      <AccountMenu email="a@example.org" onLogout={onLogout} pending failed={false} />,
    );
    await user.click(screen.getByRole("button", { name: "Signing out…" }));
    expect(onLogout).not.toHaveBeenCalled();
    rerender(<AccountMenu email="a@example.org" onLogout={onLogout} pending={false} failed />);
    expect(screen.getByRole("alert")).toHaveTextContent("Sign-out failed.");
  });
});
