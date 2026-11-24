import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { confirmationOut, mcpApi } from "@/test/mcpApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { McpTopbarSlot } from "./McpTopbarSlot";

const PAST = "2020-01-01T00:00:00Z";

/** Laisse la lecture se terminer : il n'y a rien à attendre à l'écran quand rien ne s'affiche. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 50));

function setup(confirmations: Record<string, unknown>[]) {
  server.use(...mcpApi({ confirmations }).handlers);
  renderRoutes([{ path: "/", element: <McpTopbarSlot /> }], "/");
}

describe("McpTopbarSlot", () => {
  it("topbar badge counts pending", async () => {
    setup([
      confirmationOut({ id: "a" }),
      confirmationOut({ id: "b" }),
      confirmationOut({ id: "c", status: "pending", expires_at: PAST }),
      confirmationOut({ id: "d", status: "confirmed" }),
      confirmationOut({ id: "e", status: "refused" }),
    ]);
    const link = await screen.findByRole("link", { name: "2 requests to confirm" });
    expect(link).toHaveAttribute("href", "/settings/mcp");
    expect(link).toHaveTextContent("To confirm (2)");
  });

  it("says one request in the singular", async () => {
    setup([confirmationOut()]);
    expect(await screen.findByRole("link", { name: "1 request to confirm" })).toBeInTheDocument();
  });

  it("shows nothing when nothing is waiting", async () => {
    setup([confirmationOut({ status: "expired" })]);
    await settle();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("stays silent when the request fails", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/mcp/confirmations`, () =>
        HttpResponse.json(
          { error: { code: "boom", message: "x", details: null } },
          { status: 500 },
        ),
      ),
    );
    renderRoutes([{ path: "/", element: <McpTopbarSlot /> }], "/");
    await settle();
    expect(screen.queryByRole("link")).toBeNull();
  });
});
