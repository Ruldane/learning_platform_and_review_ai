import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { postingsApi } from "@/test/postingsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { FEATURES } from "./registry";

describe("Offers page chat", () => {
  it("opens the assistant from the registered legacy Offers page", async () => {
    const path = "/carriere/offres";
    const route = FEATURES.flatMap((feature) => feature.routes).find(
      (candidate) => candidate.path === path.slice(1),
    );
    expect(route).toBeDefined();
    server.use(
      ...postingsApi().handlers,
      http.get("http://localhost:8000/api/v1/conversations/offers", () => HttpResponse.json([])),
    );
    const { user } = renderRoutes([{ ...route, path }], path);
    expect(screen.getByRole("heading", { level: 1, name: "Postings" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ask about offers" }));
    expect(screen.getByRole("dialog", { name: "Offers chat" })).toBeInTheDocument();
    expect(await screen.findByText("Start a chat to ask about your offers.")).toBeVisible();
  });
});
