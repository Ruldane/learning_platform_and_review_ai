import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { AppLayout } from "./AppLayout";

describe("AppLayout", () => {
  it("rend le lien d'évitement, la navigation, le voyant et le contenu", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter([
      { path: "/", Component: AppLayout, children: [{ index: true, element: <p>Contenu</p> }] },
    ]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });

    expect(screen.getByRole("link", { name: "Aller au contenu" })).toHaveAttribute(
      "href",
      "#contenu",
    );
    expect(screen.getByRole("navigation", { name: "Navigation principale" })).toBeInTheDocument();
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "contenu");
    expect(main).toHaveAttribute("tabindex", "-1");
    expect(main).toHaveTextContent("Contenu");
    expect(await screen.findByText("Tous les services répondent")).toBeInTheDocument();
  });
});
