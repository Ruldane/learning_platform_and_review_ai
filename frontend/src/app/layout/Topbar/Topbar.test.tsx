import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Topbar } from "./Topbar";

describe("Topbar", () => {
  it("affiche le nom de l'application et le contenu de droite", () => {
    render(<Topbar right={<span>Voyant</span>} />);
    expect(screen.getByRole("banner")).toHaveTextContent("Tremplin");
    expect(screen.getByText("Voyant")).toBeInTheDocument();
  });
});
