import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FactSourceBadges } from "./FactSourceBadges";

describe("FactSourceBadges", () => {
  it("labels each source in a stable order", () => {
    render(<FactSourceBadges sources={["january", "cv", "note", "linkedin"]} />);
    const list = screen.getByRole("list", { name: "Sources for this fact" });
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["CV", "LinkedIn", "Note", "You"]);
  });

  it("renders nothing without source", () => {
    const { container } = render(<FactSourceBadges sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
