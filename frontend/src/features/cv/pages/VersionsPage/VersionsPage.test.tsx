import { screen, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { versionOut } from "@/test/cvApi";
import { renderCv } from "@/test/cvHarness";
import { VersionsPage } from "./VersionsPage";

function setup(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv("/career/cv/versions", "/career/cv/versions", () => <VersionsPage />, api);
}

describe("VersionsPage", () => {
  it("groups the versions by posting, named after it", async () => {
    setup({
      versions: [
        versionOut({ id: "v1", number: 1 }),
        versionOut({ id: "v2", number: 2, created_at: "2026-11-12T10:00:00Z" }),
        versionOut({ id: "v3", number: 1, posting_id: "p2", review_id: "rv2" }),
      ],
      postings: [
        { id: "p1", title: "Ingénieure données", company: "Société Fictive", status: "ready" },
      ],
    });
    const first = await screen.findByRole("region", {
      name: "Versions for posting Ingénieure données, Société Fictive",
    });
    expect(within(first).getAllByRole("listitem")).toHaveLength(2);
    expect(
      screen.getByRole("region", { name: "Versions for posting deleted posting" }),
    ).toBeInTheDocument();
  });

  it("opens a version: preview of its pages and download of its PDF", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Open version 1" }));
    expect(await screen.findByAltText("Page 1 of 1 of the CV")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Download CV_Camille_Exemple_Societe_Fictive.pdf" }),
    ).toHaveAttribute("href", expect.stringContaining("/api/v1/cv/versions/v1/pdf"));
    await user.click(screen.getByRole("button", { name: "Close preview" }));
    expect(screen.queryByAltText("Page 1 of 1 of the CV")).not.toBeInTheDocument();
  });

  it("links to the review of a posting", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("link", { name: "Open review" }));
    expect(await screen.findByText("Page de la revue")).toBeInTheDocument();
  });

  it("shows an empty state whose action leads to the postings", async () => {
    const { user } = setup({ versions: [] });
    expect(await screen.findByText("No CV versions yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choose a posting" }));
    expect(await screen.findByText("Liste des offres")).toBeInTheDocument();
  });

  it("shows an error with « Retry »", async () => {
    let failing = true;
    const { user } = setup({
      versionList: () =>
        failing ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json([versionOut()]),
    });
    expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("list", { name: "CV versions" })).toBeInTheDocument();
  });
});
