import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FontGapNotice } from "./FontGapNotice";

describe("FontGapNotice", () => {
  it("lists each replaced font as a sentence", () => {
    render(
      <FontGapNotice
        gaps={[
          "The heading font was replaced with Carlito.",
          "The body font was replaced with Liberation Sans.",
        ]}
      />,
    );
    expect(screen.getByRole("complementary", { name: "Replaced fonts" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText(/replaced with Carlito/)).toBeInTheDocument();
  });

  it("renders nothing when no font was replaced", () => {
    const { container } = render(<FontGapNotice gaps={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the sentences as plain text", () => {
    render(<FontGapNotice gaps={["<b>gras</b>"]} />);
    expect(screen.getByText("<b>gras</b>")).toBeInTheDocument();
  });
});
