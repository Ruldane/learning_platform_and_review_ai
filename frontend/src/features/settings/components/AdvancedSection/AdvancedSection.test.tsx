import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AdvancedSection } from "./AdvancedSection";

describe("AdvancedSection", () => {
  it("does not mount its content while folded", () => {
    render(
      <AdvancedSection open={false} onToggle={vi.fn()}>
        <p>Contenu avancé</p>
      </AdvancedSection>,
    );
    expect(screen.getByRole("heading", { name: "Advanced mode" })).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "Show advanced mode" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Contenu avancé")).not.toBeInTheDocument();
  });

  it("shows its content when open, and asks to toggle on click", async () => {
    const onToggle = vi.fn();
    render(
      <AdvancedSection open onToggle={onToggle}>
        <p>Contenu avancé</p>
      </AdvancedSection>,
    );
    expect(screen.getByText("Contenu avancé")).toBeVisible();
    const toggle = screen.getByRole("button", { name: "Hide advanced mode" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.setup().click(toggle);
    expect(onToggle).toHaveBeenCalledOnce();
  });
});
