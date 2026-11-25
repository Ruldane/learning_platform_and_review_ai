import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { BlockView } from "../viewTypes";
import { BlockCard } from "./BlockCard";

const BLOCK: BlockView = {
  lessonTitle: "Les index en SQL",
  moduleTitle: "Bases de données",
  tasks: [
    { id: "t1", title: "Lire la leçon sur les index", type: "read", minutes: 30 },
    { id: "t2", title: "Écrire trois requêtes", type: "practice", minutes: 45 },
  ],
};

function setup(props: Partial<Parameters<typeof BlockCard>[0]> = {}) {
  const handlers = { onStart: vi.fn(), onResume: vi.fn() };
  render(<BlockCard block={BLOCK} openSessionId={null} {...handlers} {...props} />);
  return handlers;
}

describe("BlockCard", () => {
  it("shows the lesson, the module and the tasks of the block", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Les index en SQL" })).toBeInTheDocument();
    expect(screen.getByText("Module: Bases de données")).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Block tasks" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Lire la leçon sur les index");
    expect(within(list).getByText("Read")).toBeInTheDocument();
    expect(items[0]).toHaveTextContent("30 min");
    expect(within(list).getByText("Practice")).toBeInTheDocument();
    expect(screen.getByText("1 h 15 in total")).toBeInTheDocument();
  });

  it("starts the block", async () => {
    const { onStart, onResume } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Start my block" }));
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onResume).not.toHaveBeenCalled();
  });

  it("offers resume when a session is open", async () => {
    const { onStart, onResume } = setup({ openSessionId: "s1" });
    expect(screen.queryByRole("button", { name: "Start my block" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Resume my session" }));
    expect(onResume).toHaveBeenCalledTimes(1);
    expect(onStart).not.toHaveBeenCalled();
  });

  it("offers resume even when no block is left for today", () => {
    setup({ block: null, openSessionId: "s1" });
    expect(screen.getByRole("button", { name: "Resume my session" })).toBeInTheDocument();
    expect(screen.queryByText("Nothing planned for today")).not.toBeInTheDocument();
  });

  it("says there is nothing to study when there is no block and no session", () => {
    setup({ block: null });
    expect(screen.getByText("Nothing planned for today")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("disables the button while a start is on its way", () => {
    setup({ disabled: true });
    expect(screen.getByRole("button", { name: "Start my block" })).toBeDisabled();
  });
});
