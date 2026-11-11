import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VisionWarning } from "./VisionWarning";

describe("VisionWarning", () => {
  it("affiche l'avertissement quand le niveau vision n'a pas de vision", () => {
    render(<VisionWarning visible />);
    expect(screen.getByRole("note")).toHaveTextContent(
      "Le niveau vision pointe vers un modèle sans vision : la capture du design du CV est désactivée.",
    );
  });

  it("n'affiche rien sinon", () => {
    const { container } = render(<VisionWarning visible={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
