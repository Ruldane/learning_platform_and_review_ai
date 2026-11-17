import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PublicPage } from "./PublicPage";

describe("PublicPage", () => {
  it("is a page of its own whose title takes the focus", () => {
    render(
      <PublicPage title="Connexion">
        <p>Corps</p>
      </PublicPage>,
    );
    expect(screen.getByRole("main")).toContainElement(screen.getByText("Corps"));
    expect(screen.getByRole("heading", { level: 1, name: "Connexion" })).toHaveFocus();
    expect(screen.queryByRole("navigation")).toBeNull();
  });
});
