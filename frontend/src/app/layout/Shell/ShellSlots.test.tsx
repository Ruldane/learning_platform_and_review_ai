import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FeatureManifest } from "@/shared/lib/feature";
import { ShellSlots } from "./ShellSlots";

const withTopbar: FeatureManifest = {
  id: "a",
  routes: [],
  shell: { topbar: () => <span>Série de 4 jours</span> },
};
const withBoth: FeatureManifest = {
  id: "b",
  routes: [],
  shell: { topbar: () => <span>Heures</span>, overlay: () => <div role="dialog">Capture</div> },
};
const plain: FeatureManifest = { id: "c", routes: [] };

describe("ShellSlots", () => {
  it("renders the topbar slot of every feature that declares one, in order", () => {
    render(<ShellSlots slot="topbar" features={[plain, withTopbar, withBoth]} />);
    const texts = screen.getAllByText(/Série|Heures/).map((node) => node.textContent);
    expect(texts).toEqual(["Série de 4 jours", "Heures"]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders the overlay slot apart from the topbar one", () => {
    render(<ShellSlots slot="overlay" features={[withTopbar, withBoth]} />);
    expect(screen.getByRole("dialog")).toHaveTextContent("Capture");
    expect(screen.queryByText("Heures")).toBeNull();
  });

  it("renders nothing for features without a shell", () => {
    const { container } = render(<ShellSlots slot="topbar" features={[plain]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
