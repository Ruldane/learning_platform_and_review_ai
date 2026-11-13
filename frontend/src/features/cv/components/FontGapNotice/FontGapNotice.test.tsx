import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FontGapNotice } from "./FontGapNotice";

describe("FontGapNotice", () => {
  it("lists each replaced font as a sentence", () => {
    render(
      <FontGapNotice
        gaps={[
          "La police des titres n'est pas libre : remplacée par Carlito, très proche.",
          "La police du texte n'a pas d'équivalent connu : remplacée par Liberation Sans.",
        ]}
      />,
    );
    expect(screen.getByRole("complementary", { name: "Polices remplacées" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText(/remplacée par Carlito/)).toBeInTheDocument();
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
