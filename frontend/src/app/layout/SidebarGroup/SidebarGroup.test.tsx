import { render, screen } from "@testing-library/react";
import { Home } from "lucide-react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { NavGroup } from "../../buildNav";
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

  it("n'active que l'entrée sœur la plus précise (une entrée est une sous-route d'une autre)", () => {
    render(
      <MemoryRouter initialEntries={["/reglages/recherche/essai"]}>
        <SidebarGroup
          group={{
            ...base,
            items: [
              { labelKey: "nav.study", path: "/reglages/recherche" },
              { labelKey: "nav.skills", path: "/reglages/recherche/essai" },
            ],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Étudier" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Compétences" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getAllByRole("link").filter((l) => l.hasAttribute("aria-current"))).toHaveLength(
      1,
    );
  });

  it("garde le parent actif sur son propre chemin et sur une sous-route hors navigation", () => {
    const group: NavGroup = {
      ...base,
      items: [
        { labelKey: "nav.study", path: "/reglages/recherche" },
        { labelKey: "nav.skills", path: "/reglages/recherche/essai" },
      ],
    };
    const { unmount } = render(
      <MemoryRouter initialEntries={["/reglages/recherche"]}>
        <SidebarGroup group={group} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Étudier" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Compétences" })).not.toHaveAttribute("aria-current");
    unmount();
    // « Mémoire » : sous-route hors navigation, sans entrée sœur plus précise.
    render(
      <MemoryRouter initialEntries={["/memoire/documents/x"]}>
        <SidebarGroup
          group={{
            ...base,
            items: [
              { labelKey: "nav.study", path: "/memoire" },
              { labelKey: "nav.skills", path: "/autre" },
            ],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Étudier" })).toHaveAttribute("aria-current", "page");
  });

  describe("pastille d'une entrée", () => {
    const entry = (count: number | undefined) =>
      ({
        ...base,
        items: [
          { labelKey: "applications.nav.board", path: "/candidatures" },
          {
            labelKey: "applications.nav.reminders",
            path: "/candidatures/relances",
            useBadge: () => count,
            badgeLabel: (n: number) => `${n} relances dues`,
          },
        ],
      }) satisfies NavGroup;

    it("montre le nombre et le dit aux lecteurs d'écran (« 3 relances dues »)", () => {
      render(
        <MemoryRouter>
          <SidebarGroup group={entry(3)} />
        </MemoryRouter>,
      );
      const link = screen.getByRole("link", { name: /Relances/ });
      expect(link).toHaveAccessibleName("Relances, 3 relances dues");
      expect(screen.getByText("3")).toHaveAttribute("aria-hidden", "true");
    });

    it.each([[0], [undefined]])("n'affiche aucune pastille pour %s", (count) => {
      render(
        <MemoryRouter>
          <SidebarGroup group={entry(count)} />
        </MemoryRouter>,
      );
      expect(screen.getByRole("link", { name: "Relances" })).toBeInTheDocument();
      expect(screen.queryByText("0")).toBeNull();
    });

    it("n'ajoute rien aux entrées sans pastille", () => {
      render(
        <MemoryRouter>
          <SidebarGroup group={entry(2)} />
        </MemoryRouter>,
      );
      expect(screen.getByRole("link", { name: "Suivi" })).toBeInTheDocument();
    });
  });
});
