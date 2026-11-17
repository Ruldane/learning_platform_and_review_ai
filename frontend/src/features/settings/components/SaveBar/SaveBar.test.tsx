import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SaveBar } from "./SaveBar";

const labels = { save: "Enregistrer", saving: "Envoi…", saved: "Fait.", unsaved: "À enregistrer." };
const props = { pending: false, saved: false, dirty: false, blocked: true, labels };

describe("SaveBar", () => {
  it("is blocked with nothing to say when nothing changed", () => {
    render(<SaveBar {...props} />);
    expect(screen.getByRole("button", { name: "Enregistrer" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("announces unsaved changes, then the save", () => {
    const { rerender } = render(<SaveBar {...props} dirty blocked={false} />);
    expect(screen.getByRole("button", { name: "Enregistrer" })).toHaveAttribute(
      "aria-disabled",
      "false",
    );
    expect(screen.getByRole("status")).toHaveTextContent("À enregistrer.");
    rerender(<SaveBar {...props} pending dirty />);
    expect(screen.getByRole("button", { name: "Envoi…" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    rerender(<SaveBar {...props} saved />);
    expect(screen.getByRole("status")).toHaveTextContent("Fait.");
  });
});
