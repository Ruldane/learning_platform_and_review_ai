import { cleanup, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mcpApi, tokenOut } from "@/test/mcpApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { McpAccessPage } from "./McpAccessPage";

const COMMAND =
  'claude mcp add --transport http tremplin http://127.0.0.1:8000/mcp --header "Authorization: Bearer tmcp_SECRET-VALUE-123"';

const ROUTES = [{ path: "/reglages/mcp", element: <McpAccessPage /> }];

function setup(options: Parameters<typeof mcpApi>[0] = {}) {
  const api = mcpApi(options);
  server.use(...api.handlers);
  const view = renderRoutes(ROUTES, "/reglages/mcp");
  return { ...api, ...view };
}

async function createToken(user: ReturnType<typeof setup>["user"]) {
  await user.type(await screen.findByRole("textbox", { name: "Token name" }), "Portable");
  await user.click(screen.getByRole("checkbox", { name: "Skills" }));
  await user.click(screen.getByRole("button", { name: "Create token" }));
}

describe("McpAccessPage, tokens", () => {
  it("token is shown once and never again after reload", async () => {
    const { user } = setup({ tokens: [] });
    await createToken(user);
    const reveal = await screen.findByRole("region", { name: "Your token" });
    expect(within(reveal).getByText("tmcp_SECRET-VALUE-123")).toBeInTheDocument();
    expect(within(reveal).getByText(COMMAND)).toBeInTheDocument();
    await user.click(within(reveal).getByRole("button", { name: "Copy" }));
    expect(await navigator.clipboard.readText()).toBe("tmcp_SECRET-VALUE-123");
    await user.click(within(reveal).getByRole("button", { name: "I copied the token" }));
    expect(screen.queryByText("tmcp_SECRET-VALUE-123")).toBeNull();
    expect(await screen.findByText("Portable")).toBeInTheDocument();

    // « Recharger » : la page est remontée, la valeur du jeton n'existe plus nulle part.
    cleanup();
    renderRoutes(ROUTES, "/reglages/mcp");
    expect(await screen.findByText("Portable")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("tmcp_SECRET-VALUE-123");
    expect(screen.queryByRole("region", { name: "Your token" })).toBeNull();
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toContain("SECRET");
  });

  it("sends the chosen name, features, mode and duration", async () => {
    const { user, created } = setup({ tokens: [] });
    await user.type(await screen.findByRole("textbox", { name: "Token name" }), "Portable");
    await user.click(screen.getByRole("checkbox", { name: "CV and profile" }));
    await user.click(screen.getByRole("checkbox", { name: "Skills" }));
    await user.click(screen.getByRole("radio", { name: /Read and write/ }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Duration" }), "7");
    await user.click(screen.getByRole("button", { name: "Create token" }));
    await screen.findByRole("region", { name: "Your token" });
    expect(created).toEqual([
      { label: "Portable", features: ["cv", "skills"], mode: "write", expires_in_days: 7 },
    ]);
  });

  it("read-only is preselected", async () => {
    setup({ tokens: [] });
    expect(await screen.findByRole("radio", { name: /Read only/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Read and write/ })).not.toBeChecked();
    expect(screen.getByRole("combobox", { name: "Duration" })).toHaveValue("30");
    expect(screen.getByRole("button", { name: "Create token" })).toBeDisabled();
  });

  it("kill switch off hides token creation", async () => {
    setup({ enabled: false });
    expect(await screen.findByText(/no token opens anything/)).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "MCP access" })).not.toBeChecked();
    expect(screen.queryByRole("textbox", { name: "Token name" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Create token" })).toBeNull();
  });

  it("turning the switch on sends it and shows token creation", async () => {
    const { user, settingsPuts } = setup({ enabled: false });
    await user.click(await screen.findByRole("switch", { name: "MCP access" }));
    expect(await screen.findByRole("textbox", { name: "Token name" })).toBeInTheDocument();
    expect(settingsPuts).toEqual([true]);
  });

  it("lists tokens with status and revokes one", async () => {
    const { user, revoked } = setup({
      tokens: [
        tokenOut(),
        tokenOut({ id: "tk2", label: "Ancien", revoked_at: "2026-11-01T10:00:00Z" }),
        tokenOut({ id: "tk3", label: "Périmé", expires_at: "2020-01-01T00:00:00Z" }),
      ],
    });
    const tokensSection = async () =>
      within((await screen.findByRole("heading", { name: "Tokens" })).closest("section")!);
    const rowOf = async (label: string) =>
      (await (await tokensSection()).findByText(label)).closest("li")!;
    const active = within(await rowOf("Claude Code (portable)"));
    expect(active.getByText("Active")).toBeInTheDocument();
    expect(active.getByText("Read only")).toBeInTheDocument();
    expect(within(await rowOf("Ancien")).getByText("Revoked")).toBeInTheDocument();
    expect(within(await rowOf("Périmé")).getByText("Expired")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Revoke token/ })).toHaveLength(1);
    await user.click(
      screen.getByRole("button", { name: "Revoke token Claude Code (portable)" }),
    );
    await waitFor(() => expect(screen.getAllByText("Revoked")).toHaveLength(2));
    expect(revoked).toEqual(["tk1"]);
    expect(screen.queryByRole("button", { name: /^Revoke token/ })).toBeNull();
    expect(screen.getByRole("heading", { name: "Tokens" })).toHaveFocus();
  });
});
