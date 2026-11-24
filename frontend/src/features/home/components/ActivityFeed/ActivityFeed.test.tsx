import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { ActivityItemView } from "../viewTypes";
import { ActivityFeed } from "./ActivityFeed";

const NOW = new Date("2026-11-16T12:00:00Z");

const ITEMS: ActivityItemView[] = [
  {
    id: "lesson:l1:ready",
    kind: "lesson",
    at: "2026-11-16T11:55:00Z",
    title: "Leçon prête : Les jointures",
    detail: "Module SQL",
    link: "/apprendre/lecons/l1",
  },
  {
    id: "job_failed:x:failed",
    kind: "job_failed",
    at: "2026-11-16T09:00:00Z",
    title: "Une tâche planifiée a échoué",
    detail: null,
    link: null,
  },
];

function setup(props: { items?: ActivityItemView[]; hasMore?: boolean; onMore?: () => void } = {}) {
  const onMore = props.onMore ?? vi.fn();
  render(
    <MemoryRouter>
      <ActivityFeed
        items={props.items ?? ITEMS}
        hasMore={props.hasMore ?? false}
        onMore={onMore}
        now={NOW}
      />
    </MemoryRouter>,
  );
  return { onMore };
}

describe("ActivityFeed", () => {
  it("writes each date relatively, with the full date in the title and in hidden text", () => {
    setup();
    const first = screen.getAllByText(/ago/)[0]!;
    expect(first).toHaveTextContent("5 min ago");
    expect(first).toHaveAttribute("title", expect.stringMatching(/16 November 2026/));
    expect(first.querySelector(".sr-only")).toHaveTextContent(/16 November 2026/);
    expect(first).toHaveAttribute("datetime", "2026-11-16T11:55:00Z");
    expect(screen.getByText(/3 h ago/)).toBeInTheDocument();
  });

  it("links an event to its screen and leaves the others as plain text", () => {
    setup();
    expect(screen.getByRole("link", { name: "Leçon prête : Les jointures" })).toHaveAttribute(
      "href",
      "/apprendre/lecons/l1",
    );
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.getByText("Une tâche planifiée a échoué")).toBeInTheDocument();
    expect(screen.getByText("Module SQL")).toBeInTheDocument();
  });

  it("hides the kind icons from assistive technology and names the kind in hidden text", () => {
    const { container } = render(
      <MemoryRouter>
        <ActivityFeed items={ITEMS} hasMore={false} onMore={vi.fn()} now={NOW} />
      </MemoryRouter>,
    );
    const icons = container.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThanOrEqual(2);
    icons.forEach((icon) => expect(icon).toHaveAttribute("aria-hidden", "true"));
    expect(screen.getByText("Lesson :", { exact: false })).toHaveClass("sr-only");
  });

  it("offers « Voir plus » only when there is more, and calls onMore", async () => {
    const user = userEvent.setup();
    const { onMore } = setup({ hasMore: true });
    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(onMore).toHaveBeenCalledOnce();
  });

  it("has no « Voir plus » when everything is shown", () => {
    setup();
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
  });

  it("says nothing happened yet", () => {
    setup({ items: [] });
    expect(screen.getByText("Nothing new yet.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("says it is loading while the next page is read, and sends nothing more", async () => {
    const onMore = vi.fn();
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ActivityFeed items={ITEMS} hasMore loadingMore onMore={onMore} now={NOW} />
      </MemoryRouter>,
    );
    const more = screen.getByRole("button", { name: "Loading…" });
    expect(more).toHaveAttribute("aria-busy", "true");
    expect(more).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("region", { name: "Recent activity" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    await user.click(more);
    expect(onMore).not.toHaveBeenCalled();
  });
});
