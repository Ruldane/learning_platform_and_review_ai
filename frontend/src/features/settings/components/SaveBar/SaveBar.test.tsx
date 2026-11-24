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

  it("says why the button is blocked, in text tied to it", () => {
    const { rerender } = render(<SaveBar {...props} />);
    const button = () => screen.getByRole("button");
    expect(button()).toHaveAccessibleDescription("Nothing to save.");
    rerender(<SaveBar {...props} dirty invalid />);
    expect(button()).toHaveAccessibleDescription(
      "Fix the flagged fields before saving.",
    );
    rerender(<SaveBar {...props} dirty blocked={false} />);
    expect(button()).not.toHaveAccessibleDescription();
    rerender(<SaveBar {...props} dirty pending />);
    expect(button()).not.toHaveAccessibleDescription();
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
