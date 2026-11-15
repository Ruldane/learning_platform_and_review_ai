import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { applicationsManifest } from "@/features/applications/manifest";
import { applicationsApi } from "@/test/applicationsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { buildNav } from "../../buildNav";
import { Sidebar } from "./Sidebar";

function renderNav(due: number) {
  server.use(...applicationsApi({ stats: { due_reminders: due } }).handlers);
  render(
    <MemoryRouter initialEntries={["/candidatures"]}>
      <Sidebar groups={buildNav([applicationsManifest])} />
    </MemoryRouter>,
    { wrapper: createQueryWrapper() },
  );
}

describe("navigation des candidatures", () => {
  it("shows the due reminders in a badge on Relances, readable as « 3 relances dues »", async () => {
    renderNav(3);
    expect(await screen.findByRole("link", { name: "Relances, 3 relances dues" })).toHaveAttribute(
      "href",
      "/candidatures/relances",
    );
  });

  it("says « 1 relance due » in the singular", async () => {
    renderNav(1);
    expect(await screen.findByRole("link", { name: "Relances, 1 relance due" })).toBeVisible();
  });

  it("shows no badge when nothing is due", async () => {
    renderNav(0);
    await screen.findByRole("link", { name: "Suivi" });
    await waitFor(() => expect(screen.getByRole("link", { name: "Relances" })).toBeVisible());
    expect(screen.queryByText(/relances? dues?/)).toBeNull();
  });

  it("lists the board first, then the reminders and the free interview, under the Candidatures heading", () => {
    renderNav(0);
    expect(screen.getByRole("heading", { name: "Candidatures" })).toBeVisible();
    expect(screen.getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
      "/candidatures",
      "/candidatures/relances",
      "/candidatures/entretien",
    ]);
  });
});
