import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ResourceView } from "../viewTypes";
import { ResourceList } from "./ResourceList";

const RESOURCE: ResourceView = {
  id: "r1",
  title: "Documentation officielle de Python",
  url: "https://docs.python.org/3/tutorial/",
  type: "documentation",
  lang: "en",
  durationMinutes: 45,
  level: "debutant",
  author: "Python Software Foundation",
  date: "2025-10-01",
  reason: "La référence, à jour.",
  note: null,
  localCopyUrl: null,
  status: "to_read",
};

function setup(resources: ResourceView[] = [RESOURCE]) {
  const onToggleStatus = vi.fn();
  render(<ResourceList resources={resources} onToggleStatus={onToggleStatus} />);
  return { onToggleStatus, user: userEvent.setup() };
}

describe("ResourceList", () => {
  it("shows the type, language, duration, level, author, date and reason", () => {
    setup();
    const item = screen.getByRole("listitem");
    expect(item).toHaveTextContent(
      "Documentation officielle · anglais · 45 min · Débutant · par Python Software Foundation · 2025-10-01",
    );
    expect(within(item).getByText("Pourquoi : La référence, à jour.")).toBeInTheDocument();
    expect(within(item).getByText("À lire")).toBeInTheDocument();
  });

  it("opens the resource in a new tab, safely", () => {
    setup();
    const link = screen.getByRole("link", { name: /Documentation officielle de Python/ });
    expect(link).toHaveAttribute("href", "https://docs.python.org/3/tutorial/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
  });

  it("shows no link for an address that is not a web page", () => {
    setup([{ ...RESOURCE, url: null }]);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Documentation officielle de Python")).toBeInTheDocument();
  });

  it("offers the local PDF copy when there is one, otherwise the reading note", () => {
    setup([
      { ...RESOURCE, localCopyUrl: "http://api/resources/r1/file", note: "ignorée" },
      { ...RESOURCE, id: "r2", title: "Article", note: "Lire la section 2." },
    ]);
    expect(screen.getByRole("link", { name: /Copie locale \(PDF\)/ })).toHaveAttribute(
      "href",
      "http://api/resources/r1/file",
    );
    expect(screen.queryByText(/ignorée/)).toBeNull();
    expect(screen.getByText("Fiche de lecture : Lire la section 2.")).toBeInTheDocument();
  });

  it("toggles read status both ways", async () => {
    const { onToggleStatus, user } = setup([
      RESOURCE,
      { ...RESOURCE, id: "r2", title: "Déjà lue", status: "read" },
    ]);
    await user.click(
      screen.getByRole("button", {
        name: "Marquer « Documentation officielle de Python » comme lue",
      }),
    );
    expect(onToggleStatus).toHaveBeenCalledWith("r1", "read");
    expect(screen.getByText("Lue")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remettre « Déjà lue » à lire" }));
    expect(onToggleStatus).toHaveBeenCalledWith("r2", "to_read");
  });
});
