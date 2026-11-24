import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { evaluationOut, fourDrafts, projectOut, submissionOut } from "@/test/projectsApi";
import { renderProjects } from "@/test/projectsHarness";
import { PortfolioPage } from "../PortfolioPage";
import { ProjectPage } from "./ProjectPage";

const setup = (api: Parameters<typeof renderProjects>[1] = {}) =>
  renderProjects(
    (createSocket) => ({
      portfolio: <PortfolioPage />,
      project: <ProjectPage createSocket={createSocket} />,
    }),
    api,
    "/skills/portfolio/p1",
  );

const validated = (over: Record<string, unknown> = {}) =>
  projectOut("p1", {
    status: "validated",
    validated_at: "2026-11-16T12:00:00Z",
    evaluation: evaluationOut({ verdict: "validated" }),
    drafts: fourDrafts(),
    ...over,
  });

const addButton = () => screen.findByRole("button", { name: "Add to master profile" });

describe("ProjectPage : finitions", () => {
  it("lets a long link and a long description wrap instead of overflowing", async () => {
    const long = "a".repeat(600);
    setup({
      projects: [
        validated({
          submissions: [
            submissionOut({ repo_url: `https://example.org/${long}`, description: long }),
          ],
        }),
      ],
    });
    const item = (await screen.findByText(long)).closest("li")!;
    expect(item.className).toContain("[overflow-wrap:anywhere]");
    expect(item.className).toContain("min-w-0");
  });

  it("drops the « to check » warning of the entry once it is added", async () => {
    const drafts = fourDrafts({ profile_entry: { status: "to_check", flags: ["10000"] } });
    const { user } = setup({ projects: [validated({ drafts })] });
    expect(await screen.findByText(/not in your profile or your submission: 10000/)).toBeVisible();
    await user.click(await addButton());
    await screen.findByText("Added to profile (version 4)");
    expect(screen.queryByText(/not in your profile or your submission: 10000/)).toBeNull();
  });

  it("says no draft was written for a validated project that has none", async () => {
    setup({ projects: [validated({ drafts: [] })] });
    expect(await screen.findByText("No drafts have been written for this project.")).toBeVisible();
    expect(await addButton()).toHaveAttribute("aria-disabled", "false");
  });
});
