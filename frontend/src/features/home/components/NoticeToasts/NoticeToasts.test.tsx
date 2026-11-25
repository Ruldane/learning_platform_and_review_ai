import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { NoticeView } from "../viewTypes";
import { NoticeToasts } from "./NoticeToasts";

const notice = (id: string, title: string): NoticeView => ({ id, title, detail: `Détail ${id}` });

describe("NoticeToasts", () => {
  it("is a polite live region", () => {
    render(<NoticeToasts notices={[notice("a", "Leçon prête")]} onDismiss={vi.fn()} />);
    const region = screen.getByRole("region", { name: "Notifications" });
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveTextContent("Leçon prête");
    expect(region).toHaveTextContent("Détail a");
  });

  it("stays in the page, empty, when there is no notification", () => {
    render(<NoticeToasts notices={[]} onDismiss={vi.fn()} />);
    expect(screen.getByRole("region", { name: "Notifications" })).toBeEmptyDOMElement();
  });

  it("shows three notifications at most", () => {
    const notices = ["a", "b", "c", "d", "e"].map((id) => notice(id, `Titre ${id}`));
    render(<NoticeToasts notices={notices} onDismiss={vi.fn()} />);
    expect(screen.getAllByRole("button", { name: /Close notification/ })).toHaveLength(3);
    expect(screen.queryByText("Titre d")).toBeNull();
  });

  it("dismisses the selected notification using the keyboard", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(
      <NoticeToasts
        notices={[notice("a", "Leçon prête"), notice("b", "Relevé fini")]}
        onDismiss={onDismiss}
      />,
    );
    await user.tab();
    await user.tab();
    expect(
      screen.getByRole("button", { name: "Close notification: Relevé fini" }),
    ).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onDismiss).toHaveBeenCalledWith("b");
    expect(screen.getAllByText("Close")).toHaveLength(2);
  });
});

describe("NoticeToasts : la pause d'une notification", () => {
  const setup = () => {
    const onHold = vi.fn();
    render(
      <NoticeToasts
        notices={[notice("a", "Leçon prête"), notice("b", "Relevé fini")]}
        onDismiss={vi.fn()}
        onHold={onHold}
      />,
    );
    return { onHold, user: userEvent.setup() };
  };
  const toast = (title: string) => screen.getByText(title).closest("[data-notice]") as HTMLElement;

  it("notice pauses on hover and focus: a pointer over a notice holds it, leaving releases it", async () => {
    const { onHold, user } = setup();
    await user.hover(toast("Relevé fini"));
    expect(onHold).toHaveBeenLastCalledWith("b", true);
    await user.unhover(toast("Relevé fini"));
    expect(onHold).toHaveBeenLastCalledWith("b", false);
    expect(onHold).not.toHaveBeenCalledWith("a", expect.anything());
  });

  it("holds a notice while the focus is inside it, and releases it when the focus leaves", async () => {
    const { onHold, user } = setup();
    await user.tab();
    expect(onHold).toHaveBeenLastCalledWith("a", true);
    await user.tab();
    expect(onHold).toHaveBeenCalledWith("a", false);
    expect(onHold).toHaveBeenLastCalledWith("b", true);
  });

  it("keeps the hold while either the pointer or the focus is still on the notice", async () => {
    const { onHold, user } = setup();
    await user.hover(toast("Leçon prête"));
    await user.tab();
    onHold.mockClear();
    await user.unhover(toast("Leçon prête"));
    // Le focus est toujours dans la notification : elle reste en pause.
    expect(onHold).not.toHaveBeenCalledWith("a", false);
    await user.tab();
    expect(onHold).toHaveBeenCalledWith("a", false);
  });

  it("releases a notice that disappears while held, with no error", async () => {
    const onHold = vi.fn();
    const { rerender } = render(
      <NoticeToasts notices={[notice("a", "Leçon prête")]} onDismiss={vi.fn()} onHold={onHold} />,
    );
    await userEvent.setup().hover(toast("Leçon prête"));
    rerender(<NoticeToasts notices={[]} onDismiss={vi.fn()} onHold={onHold} />);
    expect(screen.getByRole("region", { name: "Notifications" })).toBeEmptyDOMElement();
  });
});
