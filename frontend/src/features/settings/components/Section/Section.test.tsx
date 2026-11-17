import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Section } from "./Section";

describe("Section", () => {
  it("titles a block of settings", () => {
    render(
      <Section title="Rythme">
        <p>Contenu</p>
      </Section>,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Rythme" })).toBeVisible();
    expect(screen.getByText("Contenu")).toBeVisible();
  });
});
