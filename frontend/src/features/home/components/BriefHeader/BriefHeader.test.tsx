import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BriefHeader } from "./BriefHeader";

describe("BriefHeader", () => {
  it("has the level 1 title, the day in words and the preparation time", () => {
    render(<BriefHeader day="2026-11-16" generatedAt="2026-11-16T06:00:00Z" />);
    expect(screen.getByRole("heading", { level: 1, name: "Ton brief du jour" })).toBeVisible();
    expect(screen.getByText(/lundi 16 novembre/)).toBeInTheDocument();
    expect(screen.getByText(/Préparé à \d{2}:\d{2}/)).toBeInTheDocument();
  });
});
