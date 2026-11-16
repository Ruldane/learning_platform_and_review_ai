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
    expect(screen.getAllByRole("button", { name: /Fermer/ })).toHaveLength(3);
    expect(screen.queryByText("Titre d")).toBeNull();
  });

  it("dismisses the notification whose Fermer button is used, with the keyboard", async () => {
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
      screen.getByRole("button", { name: "Fermer la notification : Relevé fini" }),
    ).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onDismiss).toHaveBeenCalledWith("b");
    expect(screen.getAllByText("Fermer")).toHaveLength(2);
  });
});
