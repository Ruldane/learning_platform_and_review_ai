import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it, vi } from "vitest";
import { mcpApi } from "@/test/mcpApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { McpAccessPage } from "./McpAccessPage";

const root = "*/api/v1/mcp/relay";

it("remet le code seulement au relais local et affiche son nouvel état", async () => {
  const code = `trp_${"A".repeat(43)}`;
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  const received: unknown[] = [];
  let state = "incomplete";
  server.use(
    http.get(`${root}/status`, () =>
      HttpResponse.json({ state, missing_features: state === "incomplete" ? ["lessons"] : [] }),
    ),
    http.post(`${root}/pairing`, () => HttpResponse.json({ code }, { status: 201 })),
    http.post("http://127.0.0.1:8770/pair", async ({ request }) => {
      received.push(await request.json());
      state = "paired";
      return new HttpResponse(null, { status: 204 });
    }),
    ...mcpApi().handlers,
  );
  const routes = [{ path: "/reglages/mcp", element: <McpAccessPage /> }];
  const { user } = renderRoutes(routes, "/reglages/mcp");

  expect(await screen.findByText("Périmètre incomplet")).toBeInTheDocument();
  expect(screen.getByText(/Portées manquantes.*lessons/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Renouveler l’appairage" }));
  expect(await screen.findByText("Relais connecté")).toBeInTheDocument();
  expect(received).toEqual([{ code }]);
  expect(fetchSpy).toHaveBeenCalledWith(
    "http://127.0.0.1:8770/pair",
    expect.objectContaining({ credentials: "omit", redirect: "error" }),
  );
  fetchSpy.mockRestore();
  expect(document.body).not.toHaveTextContent(code);
});
