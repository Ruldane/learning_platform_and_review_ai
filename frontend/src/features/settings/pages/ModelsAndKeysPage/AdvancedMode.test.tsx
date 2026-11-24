import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { closedGate, refusedFieldsResponse, settingsApi } from "@/test/settingsApi";
import { server } from "@/test/server";
import { agentsFixture, apiKeysFixture, modelsFixture, settingsFixture } from "../../fixtures";
import { ModelsAndKeysPage } from "./ModelsAndKeysPage";

const openai = { provider: "openai", model: "gpt-6-luna" };

function setup(
  over: Record<string, unknown> = {},
  put?: Parameters<typeof settingsApi>[0]["put"],
  agents: object[] = agentsFixture,
  gate?: Promise<void>,
) {
  const api = settingsApi({
    settings: { ...settingsFixture, ...over },
    models: modelsFixture,
    keys: apiKeysFixture,
    agents,
    put,
    gate,
  });
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/settings/models", element: <ModelsAndKeysPage /> }],
    "/settings/models",
  );
  return { ...api, ...view };
}

const showAdvanced = async (user: ReturnType<typeof setup>["user"]) => {
  await screen.findByRole("heading", { level: 1, name: "Models and keys" });
  await user.click(screen.getByRole("button", { name: "Show advanced mode" }));
  return screen.findByRole("table", { name: "Model per agent" });
};
const provider = (agent: string) => screen.getByLabelText(`Provider (${agent})`);
const model = (agent: string) => screen.getByLabelText(`Model (${agent})`);

describe("advanced mode of the models page", () => {
  it("stays folded, and reads nothing, until it is opened", async () => {
    const { counts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Models and keys" });
    const toggle = screen.getByRole("button", { name: "Show advanced mode" });
    expect(screen.getByRole("heading", { name: "Advanced mode" })).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("table", { name: "Model per agent" })).not.toBeInTheDocument();
    expect(counts.agents).toBe(0);

    await user.click(toggle);
    await screen.findByRole("table", { name: "Model per agent" });
    expect(counts.agents).toBe(1);
    await user.click(screen.getByRole("button", { name: "Hide advanced mode" }));
    expect(screen.queryByRole("table", { name: "Model per agent" })).not.toBeInTheDocument();
  });

  it("advanced mode lists agents and saves an override", async () => {
    const { puts, user } = setup({ onboarding_done: true });
    const table = await showAdvanced(user);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("rowheader")[0]?.textContent)).toEqual([
      expect.stringContaining("Scout"),
      expect.stringContaining("Strategist"),
      expect.stringContaining("Tutor"),
      expect.stringContaining("Layout designer"),
    ]); // l'ordre du registre
    // le niveau de chaque agent et le modèle de ce niveau sont écrits
    expect(within(rows[1]!).getByText("Strong")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("anthropic: claude-haiku-5-5")).toBeInTheDocument();
    expect(provider("Tutor")).toHaveValue("");
    expect(
      within(provider("Tutor")).getByRole("option", { name: "Default tier (Standard)" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Model (Tutor)")).not.toBeInTheDocument();

    await user.selectOptions(provider("Tutor"), "openai");
    await screen.findByDisplayValue("gpt-6-luna");
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      agent_overrides: { tutor: openai },
      onboarding_done: true,
      tiers: settingsFixture.tiers,
      brief_time: "07:00",
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");

    await user.selectOptions(model("Tutor"), "gpt-6.1-sol");
    await screen.findByDisplayValue("gpt-6.1-sol");
    expect(puts[1]).toMatchObject({
      agent_overrides: { tutor: { provider: "openai", model: "gpt-6.1-sol" } },
    });
  });

  it("replays a change made while saving, shows it at once, and says it is saved", async () => {
    const held = closedGate();
    const { puts, user } = setup({}, undefined, agentsFixture, held.promise);
    await showAdvanced(user);
    await user.selectOptions(provider("Tutor"), "openai");
    await waitFor(() => expect(puts).toHaveLength(1)); // le premier envoi est parti, porte fermée
    // sans attendre la réponse : le modèle suivant, puis un autre agent
    expect(provider("Tutor")).toHaveValue("openai"); // pas de retour arrière pendant l'envoi
    await user.selectOptions(model("Tutor"), "gpt-6.1-sol");
    await user.selectOptions(provider("Strategist"), "openai");
    expect(model("Tutor")).toHaveValue("gpt-6.1-sol");
    expect(screen.queryByText("Models saved.")).not.toBeInTheDocument();
    expect(puts).toHaveLength(1); // un seul envoi à la fois : les deux autres choix attendent

    held.open();
    await screen.findByText("Models saved.");
    expect(puts).toHaveLength(2); // le premier choix, puis les deux suivants d'un coup
    expect(puts[0]!.agent_overrides).toEqual({ tutor: openai });
    expect(puts[1]!.agent_overrides).toEqual({
      tutor: { provider: "openai", model: "gpt-6.1-sol" },
      strategist: openai,
    });
    expect(provider("Tutor")).toHaveValue("openai");
    expect(model("Tutor")).toHaveValue("gpt-6.1-sol");
  });

  it("falls back to what the server holds when a replayed change is refused", async () => {
    let calls = 0;
    const held = closedGate();
    const { user } = setup(
      {},
      () => (++calls === 2 ? refusedFieldsResponse("agent_overrides") : undefined),
      agentsFixture,
      held.promise,
    );
    await showAdvanced(user);
    await user.selectOptions(provider("Tutor"), "openai");
    await user.selectOptions(model("Tutor"), "gpt-6.1-sol");
    held.open();
    expect(await screen.findByRole("alert")).toHaveTextContent("no longer exists");
    await waitFor(() => expect(model("Tutor")).toHaveValue("gpt-6-luna"));
    expect(screen.queryByText("Models saved.")).not.toBeInTheDocument();
  });

  it("removing an override returns to tier", async () => {
    const { puts, user } = setup({ agent_overrides: { tutor: openai, scout: openai } });
    await showAdvanced(user);
    expect(provider("Tutor")).toHaveValue("openai");
    expect(model("Tutor")).toHaveValue("gpt-6-luna");

    await user.selectOptions(provider("Tutor"), "Default tier (Standard)");
    expect(puts).toHaveLength(1);
    expect(puts[0]!.agent_overrides).toEqual({ scout: openai }); // seule celle du tuteur part
    expect(await screen.findByLabelText("Provider (Tutor)")).toHaveValue("");
    expect(screen.queryByLabelText("Model (Tutor)")).not.toBeInTheDocument();
    expect(provider("Scout")).toHaveValue("openai");
  });

  it("waits for the model of a provider without a list before saving anything", async () => {
    const { puts, user } = setup();
    await showAdvanced(user);
    await user.selectOptions(provider("Strategist"), "glm");
    expect(puts).toEqual([]);
    const field = model("Strategist");
    expect(field).toHaveValue("");
    await user.type(field, "glm-5.3{Enter}");
    await screen.findByDisplayValue("glm-5.3");
    expect(puts).toHaveLength(1);
    expect(puts[0]!.agent_overrides).toEqual({ strategist: { provider: "glm", model: "glm-5.3" } });
  });

  it("says an agent no longer exists when the server refuses its override, no echo", async () => {
    const { user } = setup({}, () => refusedFieldsResponse("agent_overrides"));
    await showAdvanced(user);
    await user.selectOptions(provider("Tutor"), "openai");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "One of the chosen agents no longer exists: reload the page, then try again.",
    );
    expect(provider("Tutor")).toHaveValue(""); // rien n'est affiché qui n'ait été enregistré
  });

  it("keeps an override of an agent the server no longer knows, so it can be removed", async () => {
    const { puts, user } = setup({ agent_overrides: { ghost_agent: openai } });
    await showAdvanced(user);
    expect(screen.getByText("Unknown agent: set it back to the default tier.")).toBeInTheDocument();
    await user.selectOptions(provider("ghost_agent"), "Default tier");
    // une fois retirée, la ligne de l'agent inconnu disparaît
    await waitFor(() => expect(screen.queryByLabelText("Provider (ghost_agent)")).toBeNull());
    expect(puts[0]!.agent_overrides).toEqual({});
  });

  it("reports an agent list that cannot be read, and retries", async () => {
    const { user } = setup();
    let fails = true;
    server.use(
      http.get(`${API}/settings/agents`, () =>
        fails
          ? HttpResponse.json(
              { error: { code: "boom", message: "Panne des agents.", details: null } },
              { status: 500 },
            )
          : HttpResponse.json(agentsFixture),
      ),
    );
    await screen.findByRole("heading", { level: 1, name: "Models and keys" });
    await user.click(screen.getByRole("button", { name: "Show advanced mode" }));
    expect(await screen.findByText("Panne des agents.")).toBeInTheDocument();
    fails = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("table", { name: "Model per agent" });
  });
});
