import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ToolCallView } from "@/shared/realtime/types";
import { ToolChip } from "./ToolChip";

const done: ToolCallView = {
  callId: "c1",
  tool: "search",
  args: { q: "rust" },
  ok: true,
  summary: "3 résultats",
};

describe("ToolChip", () => {
  it("is a collapsed disclosure showing the tool name and its state", () => {
    render(<ToolChip call={done} />);
    const details = screen.getByText("search").closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(screen.getByText("Terminé")).toBeInTheDocument();
  });

  it("is reachable with the keyboard and reveals arguments and summary once opened", async () => {
    const user = userEvent.setup();
    render(<ToolChip call={done} />);
    await user.tab();
    // Le <summary> natif est focalisable ; Entrée/Espace l'activent comme un clic dans le navigateur.
    const summary = screen.getByText("search").closest("summary");
    expect(summary).toHaveFocus();
    expect(screen.getByText(/"q": "rust"/)).not.toBeVisible();
    await user.click(summary as HTMLElement);
    expect(screen.getByText(/"q": "rust"/)).toBeVisible();
    expect(screen.getByText("3 résultats")).toBeVisible();
  });

  it("flags a failed call with text, not only a colour", () => {
    render(<ToolChip call={{ callId: "c2", tool: "fetch", args: {}, ok: false }} />);
    expect(screen.getByText("Échec")).toBeInTheDocument();
  });

  it("shows a running call as in progress", () => {
    render(<ToolChip call={{ callId: "c3", tool: "fetch", args: {} }} />);
    expect(screen.getByText("En cours")).toBeInTheDocument();
  });
});
