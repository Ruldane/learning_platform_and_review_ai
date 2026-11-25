import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { BlockView } from "../viewTypes";
import { BlockCard } from "./BlockCard";

const BLOCK: BlockView = {
  moduleTitle: "SQL pour l'analyse",
  lessonTitle: "Les jointures",
  minutes: 45,
  tasks: [
    { title: "Lire la leçon", minutes: 20 },
    { title: "Quiz", minutes: 25 },
  ],
};

describe("BlockCard", () => {
  it("shows the module, the lesson, the total and each task", () => {
    render(<BlockCard block={BLOCK} onStart={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 2, name: "Your daily block" })).toBeVisible();
    expect(screen.getByText("Module: SQL pour l'analyse")).toBeInTheDocument();
    expect(screen.getByText("Lesson: Les jointures")).toBeInTheDocument();
    expect(screen.getByText("45 min of study")).toBeInTheDocument();
    const tasks = screen.getByRole("list", { name: "Block tasks" });
    expect(tasks).toHaveTextContent("Lire la leçon, 20 min");
    expect(tasks).toHaveTextContent("Quiz, 25 min");
  });

  it("starts the block from its button, reachable with the keyboard", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<BlockCard block={BLOCK} onStart={onStart} />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Start my block" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onStart).toHaveBeenCalledOnce();
  });

  it("says nothing is planned and offers no start button without a block", () => {
    render(<BlockCard block={null} onStart={vi.fn()} />);
    expect(screen.getByText("Nothing planned today.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("says the rubric is unavailable instead of « nothing planned » when its source failed", () => {
    render(<BlockCard block={null} unavailable onStart={vi.fn()} />);
    expect(screen.getByText("Section unavailable this morning.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
