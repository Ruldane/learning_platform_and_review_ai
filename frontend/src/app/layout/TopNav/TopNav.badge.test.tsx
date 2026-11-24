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

describe("application navigation badges", () => {
  it("announces the total number of follow-ups due on the section", async () => {
    renderNav(3);
    const section = await screen.findByRole("button", { name: "Applications, 3 follow-ups due" });
    expect(section).toHaveAccessibleName("Applications, 3 follow-ups due");
    expect(screen.getByText("3")).toHaveAttribute("aria-hidden", "true");
  });

  it('says "1 follow-up due" in the singular', async () => {
    renderNav(1);
    expect(
      await screen.findByRole("button", { name: "Applications, 1 follow-up due" }),
    ).toBeVisible();
  });

  it("keeps the badge on the follow-ups entry in the menu", async () => {
    renderNav(3);
    await userEvent.click(await screen.findByRole("button", { name: /^Applications/ }));
    const entry = await screen.findByRole("menuitem", { name: "Follow-ups, 3 follow-ups due" });
    expect(entry).toHaveAttribute("href", "/candidatures/relances");
    expect(entry).toHaveAccessibleName("Follow-ups, 3 follow-ups due");
  });

  it("lists the board first, then the reminders and the free interview", async () => {
    renderNav(0);
    await userEvent.click(screen.getByRole("button", { name: "Applications" }));
    expect(screen.getAllByRole("menuitem").map((item) => item.getAttribute("href"))).toEqual([
      "/candidatures",
      "/candidatures/relances",
      "/candidatures/entretien",
    ]);
  });

  it("shows no badge when nothing is due", () => {
    renderNav(0);
    expect(screen.getByRole("button", { name: "Applications" })).toBeVisible();
    expect(screen.queryByText(/follow-ups? due/)).toBeNull();
  });
});
