import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NoticeToast } from "./NoticeToast";

const notice = { id: "a", title: "Leçon prête", detail: "Les jointures" };

describe("NoticeToast", () => {
  it("shows the title and the detail, and closes by its own button", async () => {
    const onDismiss = vi.fn();
    render(<NoticeToast notice={notice} onDismiss={onDismiss} onHold={vi.fn()} />);
    expect(screen.getByText("Leçon prête")).toBeVisible();
    expect(screen.getByText("Les jointures")).toBeVisible();
    await userEvent.setup().click(screen.getByRole("button", { name: /Close notification/ }));
    expect(onDismiss).toHaveBeenCalledWith("a");
  });

  it("holds while hovered and releases when the pointer leaves", async () => {
    const onHold = vi.fn();
    const user = userEvent.setup();
    render(<NoticeToast notice={notice} onDismiss={vi.fn()} onHold={onHold} />);
    await user.hover(screen.getByText("Leçon prête"));
    expect(onHold).toHaveBeenLastCalledWith("a", true);
    await user.unhover(screen.getByText("Leçon prête"));
    expect(onHold).toHaveBeenLastCalledWith("a", false);
  });

  it("releases its hold when it disappears while held", async () => {
    const onHold = vi.fn();
    const user = userEvent.setup();
    const { unmount } = render(<NoticeToast notice={notice} onDismiss={vi.fn()} onHold={onHold} />);
    await user.tab();
    expect(onHold).toHaveBeenLastCalledWith("a", true);
    unmount();
    expect(onHold).toHaveBeenLastCalledWith("a", false);
  });
});
