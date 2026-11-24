import { screen, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { postingsApi, refusal } from "@/test/postingsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { GapOverviewPage } from "./GapOverviewPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  server.use(...postingsApi(api).handlers);
  return renderRoutes(
    [
      { path: "/career/gaps", element: <GapOverviewPage /> },
      { path: "/career/postings", element: <p>Postings list</p> },
      { path: "/skills", element: <p>Skills map</p> },
    ],
    "/career/gaps",
  );
}

describe("GapOverviewPage", () => {
  it("lists the most missing skills and links to the skills map", async () => {
    const { user, router } = setup();
    const list = await screen.findByRole("list", { name: "Most frequently missing skills" });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Python — 5 postings, required in 4");
    expect(items[1]).toHaveTextContent("Docker — 1 posting, never required");
    await user.click(screen.getByRole("link", { name: "View the skills map" }));
    expect(router.state.location.pathname).toBe("/skills");
  });

  it("opens the skills map from a skill", async () => {
    const { user, router } = setup();
    await user.click(await screen.findByRole("button", { name: /Python/ }));
    expect(router.state.location.pathname).toBe("/skills");
  });

  it("offers to add a posting when nothing is missing yet", async () => {
    const { user, router } = setup({ top: () => HttpResponse.json([]) });
    expect(await screen.findByText("No gaps to show")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add a posting" }));
    expect(router.state.location.pathname).toBe("/career/postings");
  });

  it("shows a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      top: () =>
        failing
          ? refusal(500, "internal_error", "The server is unavailable.")
          : HttpResponse.json([{ skill: "Python", postings: 2, required_in: 1 }]),
    });
    expect(screen.getByText("Loading gaps…")).toBeInTheDocument();
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Python — 2 postings, required in 1")).toBeInTheDocument();
  });
});
