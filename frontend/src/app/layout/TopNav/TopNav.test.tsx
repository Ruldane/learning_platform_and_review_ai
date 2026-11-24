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
    color: "var(--section-home)",
    items: [{ labelKey: "nav.home", path: "/" }],
  },
  {
    section: "learn",
    labelKey: "nav.learn",
    icon: BookOpen,
    color: "var(--section-learn)",
    items: [
      { labelKey: "program.nav.program", path: "/apprendre/programme" },
      { labelKey: "lessons.nav.lessons", path: "/apprendre/lecons" },
    ],
  },
  {
    section: "settings",
    labelKey: "nav.settings",
    icon: Settings,
    color: "var(--section-settings)",
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
      <Link to="/apprendre/lecons">Outside the menu</Link>
      <p>Outside</p>
    </MemoryRouter>,
  );
}

const section = (name: string) => screen.getByRole("button", { name });

describe("TopNav", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists one entry per section, a direct link for a one-page section", () => {
    renderNav();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(section("Learn")).toHaveAttribute("aria-haspopup", "true");
    expect(section("Learn")).toHaveAttribute("aria-expanded", "false");
    expect(section("Settings")).toBeInTheDocument();
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("centers the menus in the bar", () => {
    renderNav();
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(within(nav).getByRole("list").className).toContain("justify-center");
  });

  it("carries the colour of the active section (tint and border), not of the others", () => {
    renderNav("/apprendre/lecons");
    const active = section("Learn");
    expect(active.style.getPropertyValue("--section-color")).toBe("var(--section-learn)");
    expect(active.className).toContain(
      "bg-[color-mix(in_srgb,var(--section-color)_14%,transparent)]",
    );
    expect(active.className).toContain("border-[var(--section-color)]");
    expect(section("Settings").className).not.toContain("border-[var(--section-color)]");
    expect(section("Settings").style.getPropertyValue("--section-color")).toBe(
      "var(--section-settings)",
    );
  });

  it("tints the one-page section link on its page", () => {
    renderNav("/");
    const link = screen.getByRole("link", { name: "Home" });
    expect(link.style.getPropertyValue("--section-color")).toBe("var(--section-home)");
    expect(link.className).toContain("border-[var(--section-color)]");
  });

  it("opens the sub-menu on click, in the order of the navigation", async () => {
    renderNav();
    await userEvent.click(section("Learn"));
    expect(section("Learn")).toHaveAttribute("aria-expanded", "true");
    const items = within(screen.getByRole("menu", { name: "Learn" })).getAllByRole("menuitem");
    expect(items.map((item) => item.getAttribute("href"))).toEqual([
      "/apprendre/programme",
      "/apprendre/lecons",
    ]);
  });

  it("highlights the current section and the current page (aria-current)", async () => {
    renderNav("/apprendre/lecons");
    expect(section("Learn")).toHaveAttribute("data-active", "true");
    expect(section("Settings")).not.toHaveAttribute("data-active");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
    await userEvent.click(section("Learn"));
    expect(screen.getByRole("menuitem", { name: "Lessons" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("menuitem", { name: "Programs" })).not.toHaveAttribute("aria-current");
  });

  it("marks the one-page section link as current on its page", () => {
    renderNav("/");
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });

  it("closes on Escape and gives the focus back to the button", async () => {
    renderNav();
    await userEvent.click(section("Learn"));
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Programs" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(section("Learn")).toHaveFocus();
    expect(section("Learn")).toHaveAttribute("aria-expanded", "false");
  });

  it("closes on a click outside", async () => {
    renderNav();
    await userEvent.click(section("Learn"));
    await userEvent.click(screen.getByText("Outside"));
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("moves with the up and down arrows inside the sub-menu", async () => {
    renderNav();
    await userEvent.click(section("Learn"));
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Programs" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Lessons" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Programs" })).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    expect(screen.getByRole("menuitem", { name: "Lessons" })).toHaveFocus();
  });

  it("opens with the arrow down from the button and focuses the first page", async () => {
    renderNav();
    section("Settings").focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Costs" })).toHaveFocus();
  });

  it("keeps a single sub-menu open at a time", async () => {
    renderNav();
    await userEvent.click(section("Learn"));
    await userEvent.click(section("Settings"));
    expect(screen.getAllByRole("menu")).toHaveLength(1);
    expect(section("Learn")).toHaveAttribute("aria-expanded", "false");
    expect(section("Settings")).toHaveAttribute("aria-expanded", "true");
  });

  it("closes after a navigation, from the menu or from elsewhere", async () => {
    renderNav();
    await userEvent.click(section("Learn"));
    await userEvent.click(screen.getByRole("menuitem", { name: "Programs" }));
    expect(screen.queryByRole("menu")).toBeNull();
    await userEvent.click(section("Settings"));
    await userEvent.click(screen.getByRole("link", { name: "Outside the menu" }));
    expect(screen.queryByRole("menu")).toBeNull();
  });

  describe("narrow screen", () => {
    const narrow = () =>
      vi.stubGlobal("matchMedia", () => ({
        matches: true,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }));

    it("switches below 1024 px", () => {
      const queries: string[] = [];
      vi.stubGlobal("matchMedia", (query: string) => {
        queries.push(query);
        return {
          matches: false,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
        };
      });
      renderNav();
      expect(queries).toContain("(max-width: 1023px)");
    });

    it("shows a Menu button instead of the bar, and a panel with every section and page", async () => {
      narrow();
      renderNav("/apprendre/lecons");
      expect(screen.queryByRole("button", { name: "Learn" })).toBeNull();
      const menu = screen.getByRole("button", { name: "Menu" });
      expect(menu).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByRole("link", { name: "Lessons" })).toBeNull();
      await userEvent.click(menu);
      expect(menu).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByRole("heading", { name: "Learn" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
      expect(screen.getByRole("link", { name: "Lessons" })).toHaveAttribute("aria-current", "page");
      expect(screen.getByRole("link", { name: "My data" })).toBeInTheDocument();
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
      await userEvent.click(screen.getByRole("link", { name: "Programs" }));
      expect(menu).toHaveAttribute("aria-expanded", "false");
    });
  });
});
