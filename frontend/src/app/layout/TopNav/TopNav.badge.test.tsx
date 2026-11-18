import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { applicationsManifest } from "@/features/applications/manifest";
import { applicationsApi } from "@/test/applicationsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { buildNav } from "../../buildNav";
import { TopNav } from "./TopNav";

function renderNav(due: number) {
  server.use(...applicationsApi({ stats: { due_reminders: due } }).handlers);
  render(
    <MemoryRouter initialEntries={["/candidatures"]}>
      <TopNav groups={buildNav([applicationsManifest])} />
    </MemoryRouter>,
    { wrapper: createQueryWrapper() },
  );
}

describe("pastilles de la navigation des candidatures", () => {
  it("sums the due reminders on the section, read as « 3 relances dues »", async () => {
    renderNav(3);
    const section = await screen.findByRole("button", { name: "Candidatures, 3 relances dues" });
    expect(section).toHaveAccessibleName("Candidatures, 3 relances dues");
    expect(screen.getByText("3")).toHaveAttribute("aria-hidden", "true");
  });

  it("says « 1 relance due » in the singular", async () => {
    renderNav(1);
    expect(
      await screen.findByRole("button", { name: "Candidatures, 1 relance due" }),
    ).toBeVisible();
  });

  it("keeps the badge on the Relances entry of the sub-menu", async () => {
    renderNav(3);
    await userEvent.click(await screen.findByRole("button", { name: /^Candidatures/ }));
    const entry = await screen.findByRole("menuitem", { name: "Relances, 3 relances dues" });
    expect(entry).toHaveAttribute("href", "/candidatures/relances");
    expect(entry).toHaveAccessibleName("Relances, 3 relances dues");
  });

  it("lists the board first, then the reminders and the free interview", async () => {
    renderNav(0);
    await userEvent.click(screen.getByRole("button", { name: "Candidatures" }));
    expect(screen.getAllByRole("menuitem").map((item) => item.getAttribute("href"))).toEqual([
      "/candidatures",
      "/candidatures/relances",
      "/candidatures/entretien",
    ]);
  });

  it("shows no badge when nothing is due", () => {
    renderNav(0);
    expect(screen.getByRole("button", { name: "Candidatures" })).toBeVisible();
    expect(screen.queryByText(/relances? dues?/)).toBeNull();
  });
});
