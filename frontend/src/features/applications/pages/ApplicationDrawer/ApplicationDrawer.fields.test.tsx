import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { applicationOut, reminderOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { applicationsManifest } from "../../manifest";

async function openDrawer(api: Parameters<typeof renderApplications>[2] = {}) {
  renderApplications(applicationsManifest.routes, "/applications/a1", {
    applications: [applicationOut()],
    ...api,
  });
  const dialog = await screen.findByRole("dialog", { name: /,/ });
  await within(dialog).findByLabelText("Company");
  return dialog;
}

describe("ApplicationDrawer, headings and fields", () => {
  it("nests the reminder cards under its section title (h2 title, h3 section, h4 card)", async () => {
    const dialog = await openDrawer({ reminders: [reminderOut()] });
    const card = await within(dialog).findByRole("article");
    expect(
      within(card).getByRole("heading", { level: 4, name: "LinkedIn follow-up after 7 days" }),
    ).toBeVisible();
    expect(within(dialog).queryByRole("heading", { level: 1 })).toBeNull();
    expect(within(dialog).getAllByRole("heading", { level: 2 })).toHaveLength(1);
  });

  it("caps the company and the title at 200 characters, as the server does", async () => {
    const dialog = await openDrawer();
    expect(within(dialog).getByLabelText("Company")).toHaveAttribute("maxLength", "200");
    expect(within(dialog).getByLabelText("Role")).toHaveAttribute("maxLength", "200");
  });
});
