import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KIND_COLORS } from "../kindColors";
import { KindBadge } from "./KindBadge";

describe("KindBadge", () => {
  it("writes the kind name, never the color alone", () => {
    render(<KindBadge kind="lecon" />);
    expect(screen.getByText("Leçon")).toBeInTheDocument();
  });

  it("uses the color of the kind", () => {
    render(<KindBadge kind="decision" />);
    expect(screen.getByText("Décision")).toHaveStyle({ color: KIND_COLORS.decision });
  });
});
