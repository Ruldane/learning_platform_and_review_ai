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
    expect(screen.getByRole("heading", { level: 2, name: "Ton bloc du jour" })).toBeVisible();
    expect(screen.getByText("Module : SQL pour l'analyse")).toBeInTheDocument();
    expect(screen.getByText("Leçon : Les jointures")).toBeInTheDocument();
    expect(screen.getByText("45 min d'étude")).toBeInTheDocument();
    const tasks = screen.getByRole("list", { name: "Tâches du bloc" });
    expect(tasks).toHaveTextContent("Lire la leçon, 20 min");
    expect(tasks).toHaveTextContent("Quiz, 25 min");
  });

  it("starts the block from its button, reachable with the keyboard", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<BlockCard block={BLOCK} onStart={onStart} />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Commencer mon bloc" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onStart).toHaveBeenCalledOnce();
  });

  it("says nothing is planned and offers no start button without a block", () => {
    render(<BlockCard block={null} onStart={vi.fn()} />);
    expect(screen.getByText("Rien de prévu aujourd'hui.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
