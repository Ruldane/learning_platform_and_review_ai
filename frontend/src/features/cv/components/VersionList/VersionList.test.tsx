import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { VersionView } from "../viewTypes";
import { VersionList } from "./VersionList";

const version = (number: number, patch: Partial<VersionView> = {}): VersionView => ({
  id: `v${number}`,
  number,
  status: "ready",
  pageCount: 1,
  originalPageCount: 1,
  filename: `CV_Camille-Exemple_${number}.pdf`,
  createdAt: "2026-11-12T12:00:00Z",
  failureReason: null,
  ...patch,
});

describe("VersionList", () => {
  it("lists the newest first with state, pages, day and file", () => {
    render(
      <VersionList
        versions={[
          version(1),
          version(3, { pageCount: 2 }),
          version(2, { status: "rendering", pageCount: null }),
        ]}
        onOpen={() => undefined}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => within(item).getByText(/^Version/).textContent)).toEqual([
      "Version 3",
      "Version 2",
      "Version 1",
    ]);
    expect(items[0]).toHaveTextContent("Prête");
    expect(items[0]).toHaveTextContent("2 pages");
    expect(items[0]).toHaveTextContent("Créée le 12/11/2026");
    expect(items[0]).toHaveTextContent("CV_Camille-Exemple_3.pdf");
    expect(items[1]).toHaveTextContent("Génération en cours");
    expect(items[2]).toHaveTextContent("1 page");
  });

  it("opens a version by its identifier, with a named button", async () => {
    const onOpen = vi.fn();
    render(<VersionList versions={[version(1), version(2)]} onOpen={onOpen} />);
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir la version 1" }));
    expect(onOpen).toHaveBeenCalledWith("v1");
  });

  it("opens a version with too many pages, but not one that is rendering or failed", () => {
    render(
      <VersionList
        versions={[
          version(1, { status: "pages_exceeded", pageCount: 2 }),
          version(2, { status: "rendering", pageCount: null }),
          version(3, { status: "failed", pageCount: null, failureReason: "Le rendu a échoué." }),
        ]}
        onOpen={() => undefined}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Ouvrir la version 1" })).toBeInTheDocument();
    expect(screen.getByText("Le rendu a échoué.")).toBeInTheDocument();
    expect(screen.getByText("Trop de pages")).toBeInTheDocument();
  });

  it("says when there is no version", () => {
    render(<VersionList versions={[]} onOpen={() => undefined} />);
    expect(screen.getByText("Aucune version générée pour l'instant.")).toBeInTheDocument();
  });
});
