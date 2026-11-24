import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { settingsFixture } from "@/features/settings/fixtures";
import { apiBaseUrl } from "@/shared/api/client";
import { applicationsApi } from "@/test/applicationsApi";
import { authApi, camille } from "@/test/authApi";
import { mcpApi } from "@/test/mcpApi";
import { postingsApi } from "@/test/postingsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { settingsApi } from "@/test/settingsApi";
import { studyApi } from "@/test/studyApi";
import { FEATURES } from "./registry";
import { buildRoutes } from "./router";

const routes = buildRoutes(FEATURES);
const API = `${apiBaseUrl}/api/v1`;

describe("Offers page chat", () => {
  beforeEach(() => {
    server.use(
      ...authApi({ me: camille }).handlers,
      ...settingsApi({ settings: settingsFixture }).handlers,
      ...applicationsApi().handlers,
      ...mcpApi().handlers,
      ...postingsApi().handlers,
      ...studyApi().handlers,
      http.get(`${API}/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
      http.get(`${API}/study-return`, () => HttpResponse.json({ reminder_due: false })),
      http.get(`${API}/lab/preferences`, () => HttpResponse.json({ pinned: [], tour: "pending" })),
      http.get(`${API}/activity`, () => HttpResponse.json({ items: [], latest_at: null })),
      http.get(`${API}/conversations/offers`, () => HttpResponse.json([])),
    );
  });

  it("opens the assistant after redirecting the old postings URL", async () => {
    const { router, user } = renderRoutes(routes, {
      pathname: "/carriere/offres",
      search: "?source=bookmark",
      hash: "#postings",
      state: { source: "activity" },
    });
    await screen.findByRole("heading", { level: 1, name: "Postings" });
    expect(router.state.location).toMatchObject({
      pathname: "/career/postings",
      search: "?source=bookmark",
      hash: "#postings",
      state: { source: "activity" },
    });
    expect(router.state.historyAction).toBe("REPLACE");
    await user.click(screen.getByRole("button", { name: "Ask about offers" }));
    expect(screen.getByRole("dialog", { name: "Offers chat" })).toBeInTheDocument();
    expect(await screen.findByText("Start a chat to ask about your offers.")).toBeVisible();
  });

  it.each([
    ["/carriere/offres/p1", "/career/postings/p1", "Ingénieure données"],
    ["/carriere/ecarts", "/career/gaps", "Gaps"],
  ])("redirects %s to %s", async (legacy, destination, heading) => {
    const { router } = renderRoutes(routes, legacy);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(destination);
  });
});
