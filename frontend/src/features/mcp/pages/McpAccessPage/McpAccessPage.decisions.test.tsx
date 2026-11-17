import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { actionOut, callRow, changeOut, mcpApi } from "@/test/mcpApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { McpAccessPage } from "./McpAccessPage";

function setup(options: Parameters<typeof mcpApi>[0] = {}) {
  const api = mcpApi(options);
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/reglages/mcp", element: <McpAccessPage /> }],
    "/reglages/mcp",
  );
  return { ...api, ...view };
}

describe("McpAccessPage, À confirmer", () => {
  it("confirm twice sends once", async () => {
    const { user, decisions } = setup({ decideDelayMs: 60 });
    const button = await screen.findByRole("button", { name: "Confirmer" });
    await user.dblClick(button);
    expect(await screen.findByText("Confirmée")).toBeInTheDocument();
    expect(decisions).toEqual(["confirm:cf1"]);
    expect(screen.queryByRole("button", { name: "Confirmer" })).toBeNull();
    expect(screen.getByRole("heading", { name: "À confirmer" })).toHaveFocus();
  });

  it("refusing sends the refusal and removes the buttons", async () => {
    const { user, decisions } = setup();
    await user.click(await screen.findByRole("button", { name: "Refuser" }));
    expect(await screen.findByText("Refusée")).toBeInTheDocument();
    expect(decisions).toEqual(["refuse:cf1"]);
  });

  it("shows a readable error when the request can no longer be decided", async () => {
    const { user } = setup();
    server.use(
      http.post(`${API}/mcp/confirmations/:id/confirm`, () =>
        HttpResponse.json(
          { error: { code: "expired", message: "La demande a expiré.", details: null } },
          { status: 409 },
        ),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Confirmer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La demande a expiré.");
    expect(screen.getByRole("button", { name: "Confirmer" })).toBeEnabled();
  });

  it("says when nothing is waiting", async () => {
    setup({ confirmations: [] });
    expect(await screen.findByText("Rien à confirmer.")).toBeInTheDocument();
  });
});

describe("McpAccessPage, historique", () => {
  it("undo sends the call id and marks the change as undone", async () => {
    const { user, undone } = setup({
      changes: [changeOut(), changeOut({ call_id: "call0", undone_at: "2026-11-17T09:30:00Z" })],
    });
    await user.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(undone).toEqual(["call1"]);
    expect(await screen.findByRole("heading", { name: "Historique" })).toHaveFocus();
  });

  it("shows the reason when an undo is refused", async () => {
    const { user } = setup({
      undoError: { status: 409, code: "undo_refused", message: "La ligne a changé depuis." },
    });
    await user.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La ligne a changé depuis.");
  });

  it("lists the calls with level, code and duration, never a content", async () => {
    setup({ calls: [callRow(), callRow({ id: "c2", action: "cv_list", level: 1, code: 429 })] });
    const table = await screen.findByRole("table", { name: "Appels de Claude" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[0]!).getByText("skills_add_proof")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("Écriture annulable")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("84 ms")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("429")).toBeInTheDocument();
  });
});

describe("McpAccessPage, appels refusés", () => {
  it("shows a call refused before the tool was found, from an unknown token", async () => {
    setup({
      calls: [callRow({ id: "c0", action: "unknown", level: 0, code: 401, token_id: null })],
    });
    const table = await screen.findByRole("table", { name: "Appels de Claude" });
    const row = within(within(table).getAllByRole("row")[1]!);
    expect(row.getByText("Refusé")).toBeInTheDocument();
    expect(row.getByText("jeton inconnu")).toBeInTheDocument();
    expect(row.getByText("401")).toBeInTheDocument();
  });
});

describe("McpAccessPage, niveaux", () => {
  it("levels table filters by feature", async () => {
    const { user } = setup({
      actions: [
        actionOut(),
        actionOut({ name: "skills_add_proof", feature: "skills", level: 2 }),
        actionOut({ name: "postings_delete", feature: "postings", level: 3 }),
      ],
    });
    const table = await screen.findByRole("table", { name: "Outils exposés au MCP" });
    expect(within(table).getAllByRole("row")).toHaveLength(4);
    await user.selectOptions(screen.getByRole("combobox", { name: "Feature" }), "skills");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(within(rows[1]!).getByText("skills_add_proof")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("Écriture annulable")).toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "Feature" }), "");
    expect(within(table).getAllByRole("row")).toHaveLength(4);
  });

  it("explains the four levels, the last one never exposed", async () => {
    setup();
    expect(await screen.findByText(/Niveau 4/)).toHaveTextContent("jamais ouvert");
  });
});
