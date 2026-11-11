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
});
