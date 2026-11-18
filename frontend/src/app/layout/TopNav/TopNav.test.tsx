import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BookOpen, Home, Settings } from "lucide-react";
import { Link, MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NavGroup } from "../../buildNav";
import { TopNav } from "./TopNav";

const groups: NavGroup[] = [
  {
    section: "home",
    labelKey: "nav.home",
    icon: Home,
    items: [{ labelKey: "nav.home", path: "/" }],
  },
  {
    section: "learn",
    labelKey: "nav.learn",
    icon: BookOpen,
    items: [
      { labelKey: "program.nav.program", path: "/apprendre/programme" },
      { labelKey: "lessons.nav.lessons", path: "/apprendre/lecons" },
    ],
  },
  {
    section: "settings",
    labelKey: "nav.settings",
    icon: Settings,
    items: [
      { labelKey: "costs.nav.costs", path: "/reglages/couts" },
      { labelKey: "account.nav.data", path: "/reglages/donnees" },
    ],
  },
];

function renderNav(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TopNav groups={groups} />
      <Link to="/apprendre/lecons">Hors menu</Link>
      <p>Dehors</p>
    </MemoryRouter>,
  );
}

const section = (name: string) => screen.getByRole("button", { name });

describe("TopNav", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists one entry per section, a direct link for a one-page section", () => {
    renderNav();
    expect(screen.getByRole("navigation", { name: "Navigation principale" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Accueil" })).toHaveAttribute("href", "/");
    expect(section("Apprendre")).toHaveAttribute("aria-haspopup", "true");
    expect(section("Apprendre")).toHaveAttribute("aria-expanded", "false");
    expect(section("Réglages")).toBeInTheDocument();
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("opens the sub-menu on click, in the order of the navigation", async () => {
    renderNav();
    await userEvent.click(section("Apprendre"));
    expect(section("Apprendre")).toHaveAttribute("aria-expanded", "true");
    const items = within(screen.getByRole("menu", { name: "Apprendre" })).getAllByRole("menuitem");
    expect(items.map((item) => item.getAttribute("href"))).toEqual([
      "/apprendre/programme",
      "/apprendre/lecons",
    ]);
  });

  it("highlights the current section and the current page (aria-current)", async () => {
    renderNav("/apprendre/lecons");
    expect(section("Apprendre")).toHaveAttribute("data-active", "true");
    expect(section("Réglages")).not.toHaveAttribute("data-active");
    expect(screen.getByRole("link", { name: "Accueil" })).not.toHaveAttribute("aria-current");
    await userEvent.click(section("Apprendre"));
    expect(screen.getByRole("menuitem", { name: "Leçons" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("menuitem", { name: "Programme" })).not.toHaveAttribute("aria-current");
  });

  it("marks the one-page section link as current on its page", () => {
    renderNav("/");
    expect(screen.getByRole("link", { name: "Accueil" })).toHaveAttribute("aria-current", "page");
  });

  it("closes on Escape and gives the focus back to the button", async () => {
    renderNav();
    await userEvent.click(section("Apprendre"));
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Programme" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(section("Apprendre")).toHaveFocus();
    expect(section("Apprendre")).toHaveAttribute("aria-expanded", "false");
  });

  it("closes on a click outside", async () => {
    renderNav();
    await userEvent.click(section("Apprendre"));
    await userEvent.click(screen.getByText("Dehors"));
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("moves with the up and down arrows inside the sub-menu", async () => {
    renderNav();
    await userEvent.click(section("Apprendre"));
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Programme" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Leçons" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Programme" })).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    expect(screen.getByRole("menuitem", { name: "Leçons" })).toHaveFocus();
  });

  it("opens with the arrow down from the button and focuses the first page", async () => {
    renderNav();
    section("Réglages").focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: /Coûts/ })).toHaveFocus();
  });

  it("keeps a single sub-menu open at a time", async () => {
    renderNav();
    await userEvent.click(section("Apprendre"));
    await userEvent.click(section("Réglages"));
    expect(screen.getAllByRole("menu")).toHaveLength(1);
    expect(section("Apprendre")).toHaveAttribute("aria-expanded", "false");
    expect(section("Réglages")).toHaveAttribute("aria-expanded", "true");
  });

  it("closes after a navigation, from the menu or from elsewhere", async () => {
    renderNav();
    await userEvent.click(section("Apprendre"));
    await userEvent.click(screen.getByRole("menuitem", { name: "Programme" }));
    expect(screen.queryByRole("menu")).toBeNull();
    await userEvent.click(section("Réglages"));
    await userEvent.click(screen.getByRole("link", { name: "Hors menu" }));
    expect(screen.queryByRole("menu")).toBeNull();
  });

  describe("narrow screen", () => {
    const narrow = () =>
      vi.stubGlobal("matchMedia", () => ({
        matches: true,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }));

    it("shows a Menu button instead of the bar, and a panel with every section and page", async () => {
      narrow();
      renderNav("/apprendre/lecons");
      expect(screen.queryByRole("button", { name: "Apprendre" })).toBeNull();
      const menu = screen.getByRole("button", { name: "Menu" });
      expect(menu).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByRole("link", { name: "Leçons" })).toBeNull();
      await userEvent.click(menu);
      expect(menu).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByRole("heading", { name: "Apprendre" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Accueil" })).toHaveAttribute("href", "/");
      expect(screen.getByRole("link", { name: "Leçons" })).toHaveAttribute("aria-current", "page");
      expect(screen.getByRole("link", { name: "Mes données" })).toBeInTheDocument();
    });

    it("closes the panel on Escape (focus back on Menu) and after a navigation", async () => {
      narrow();
      renderNav();
      const menu = screen.getByRole("button", { name: "Menu" });
      await userEvent.click(menu);
      await userEvent.keyboard("{Escape}");
      expect(menu).toHaveAttribute("aria-expanded", "false");
      expect(menu).toHaveFocus();
      await userEvent.click(menu);
      await userEvent.click(screen.getByRole("link", { name: "Programme" }));
      expect(menu).toHaveAttribute("aria-expanded", "false");
    });
  });
});
