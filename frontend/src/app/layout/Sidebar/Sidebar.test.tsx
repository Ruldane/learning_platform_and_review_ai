import { render, screen } from "@testing-library/react";
import { Home, Settings } from "lucide-react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { NavGroup } from "../../buildNav";
import { Sidebar } from "./Sidebar";

const groups: NavGroup[] = [
  {
    section: "home",
    labelKey: "nav.home",
    icon: Home,
    items: [{ labelKey: "nav.home", path: "/" }],
  },
  {
    section: "settings",
    labelKey: "nav.settings",
    icon: Settings,
    items: [{ labelKey: "nav.settings", path: "/reglages" }],
  },
];

describe("Sidebar", () => {
  it("marque l'entrée active avec aria-current", () => {
    render(
      <MemoryRouter initialEntries={["/reglages"]}>
        <Sidebar groups={groups} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("navigation", { name: "Navigation principale" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Réglages" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Accueil" })).not.toHaveAttribute("aria-current");
  });
});
