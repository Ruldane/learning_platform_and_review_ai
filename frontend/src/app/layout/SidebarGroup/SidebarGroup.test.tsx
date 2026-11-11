import { render, screen } from "@testing-library/react";
import { Home } from "lucide-react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { SidebarGroup } from "./SidebarGroup";

const base = { section: "learn", labelKey: "nav.learn", icon: Home } as const;

describe("SidebarGroup", () => {
  it("affiche un simple lien pour une section à une seule entrée", () => {
    render(
      <MemoryRouter>
        <SidebarGroup group={{ ...base, items: [{ labelKey: "nav.learn", path: "/apprendre" }] }} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Apprendre" })).toHaveAttribute("href", "/apprendre");
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  });

  it("affiche un titre de section au-dessus de plusieurs entrées", () => {
    render(
      <MemoryRouter>
        <SidebarGroup
          group={{
            ...base,
            items: [
              { labelKey: "nav.study", path: "/a" },
              { labelKey: "nav.skills", path: "/b" },
            ],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Apprendre" })).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(2);
  });

  it("garde l'entrée active sur une sous-route (section à une seule entrée)", () => {
    render(
      <MemoryRouter initialEntries={["/apprendre/cles"]}>
        <SidebarGroup group={{ ...base, items: [{ labelKey: "nav.learn", path: "/apprendre" }] }} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Apprendre" })).toHaveAttribute("aria-current", "page");
  });

  it("n'active pas « / » sur une autre page, et active l'entrée courante (plusieurs entrées)", () => {
    render(
      <MemoryRouter initialEntries={["/x/detail"]}>
        <SidebarGroup
          group={{
            ...base,
            items: [
              { labelKey: "nav.home", path: "/" },
              { labelKey: "nav.study", path: "/x" },
            ],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Accueil" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Étudier" })).toHaveAttribute("aria-current", "page");
  });

  it("active « / » sur la page d'accueil", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <SidebarGroup group={{ ...base, items: [{ labelKey: "nav.home", path: "/" }] }} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Accueil" })).toHaveAttribute("aria-current", "page");
  });
});
