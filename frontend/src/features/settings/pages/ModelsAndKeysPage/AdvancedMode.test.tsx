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
    [{ path: "/reglages/modeles", element: <ModelsAndKeysPage /> }],
    "/reglages/modeles",
  );
  return { ...api, ...view };
}

const showAdvanced = async (user: ReturnType<typeof setup>["user"]) => {
  await screen.findByRole("heading", { level: 1, name: "Modèles et clés" });
  await user.click(screen.getByRole("button", { name: "Afficher le mode avancé" }));
  return screen.findByRole("table", { name: "Modèle par agent" });
};
const provider = (agent: string) => screen.getByLabelText(`Fournisseur (${agent})`);
const model = (agent: string) => screen.getByLabelText(`Modèle (${agent})`);

describe("advanced mode of the models page", () => {
  it("stays folded, and reads nothing, until it is opened", async () => {
    const { counts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Modèles et clés" });
    const toggle = screen.getByRole("button", { name: "Afficher le mode avancé" });
    expect(screen.getByRole("heading", { name: "Mode avancé" })).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("table", { name: "Modèle par agent" })).not.toBeInTheDocument();
    expect(counts.agents).toBe(0);

    await user.click(toggle);
    await screen.findByRole("table", { name: "Modèle par agent" });
    expect(counts.agents).toBe(1);
    await user.click(screen.getByRole("button", { name: "Masquer le mode avancé" }));
    expect(screen.queryByRole("table", { name: "Modèle par agent" })).not.toBeInTheDocument();
  });

  it("advanced mode lists agents and saves an override", async () => {
    const { puts, user } = setup({ onboarding_done: true });
    const table = await showAdvanced(user);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("rowheader")[0]?.textContent)).toEqual([
      expect.stringContaining("Éclaireur"),
      expect.stringContaining("Stratège"),
      expect.stringContaining("Tuteur"),
      expect.stringContaining("Maquettiste"),
    ]); // l'ordre du registre
    // le niveau de chaque agent et le modèle de ce niveau sont écrits
    expect(within(rows[1]!).getByText("Fort")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("anthropic : claude-haiku-5-5")).toBeInTheDocument();
    expect(provider("Tuteur")).toHaveValue("");
    expect(
      within(provider("Tuteur")).getByRole("option", { name: "Niveau par défaut (Standard)" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Modèle (Tuteur)")).not.toBeInTheDocument();

    await user.selectOptions(provider("Tuteur"), "openai");
    await screen.findByDisplayValue("gpt-6-luna");
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      agent_overrides: { tutor: openai },
      onboarding_done: true,
      tiers: settingsFixture.tiers,
      brief_time: "07:00",
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");

    await user.selectOptions(model("Tuteur"), "gpt-6.1-sol");
    await screen.findByDisplayValue("gpt-6.1-sol");
    expect(puts[1]).toMatchObject({
      agent_overrides: { tutor: { provider: "openai", model: "gpt-6.1-sol" } },
    });
  });

  it("replays a change made while saving, shows it at once, and says it is saved", async () => {
    const held = closedGate();
    const { puts, user } = setup({}, undefined, agentsFixture, held.promise);
    await showAdvanced(user);
    await user.selectOptions(provider("Tuteur"), "openai");
    await waitFor(() => expect(puts).toHaveLength(1)); // le premier envoi est parti, porte fermée
    // sans attendre la réponse : le modèle suivant, puis un autre agent
    expect(provider("Tuteur")).toHaveValue("openai"); // pas de retour arrière pendant l'envoi
    await user.selectOptions(model("Tuteur"), "gpt-6.1-sol");
    await user.selectOptions(provider("Stratège"), "openai");
    expect(model("Tuteur")).toHaveValue("gpt-6.1-sol");
    expect(screen.queryByText("Modèles enregistrés.")).not.toBeInTheDocument();
    expect(puts).toHaveLength(1); // un seul envoi à la fois : les deux autres choix attendent

    held.open();
    await screen.findByText("Modèles enregistrés.");
    expect(puts).toHaveLength(2); // le premier choix, puis les deux suivants d'un coup
    expect(puts[0]!.agent_overrides).toEqual({ tutor: openai });
    expect(puts[1]!.agent_overrides).toEqual({
      tutor: { provider: "openai", model: "gpt-6.1-sol" },
      strategist: openai,
    });
    expect(provider("Tuteur")).toHaveValue("openai");
    expect(model("Tuteur")).toHaveValue("gpt-6.1-sol");
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
    await user.selectOptions(provider("Tuteur"), "openai");
    await user.selectOptions(model("Tuteur"), "gpt-6.1-sol");
    held.open();
    expect(await screen.findByRole("alert")).toHaveTextContent("n'existe plus");
    await waitFor(() => expect(model("Tuteur")).toHaveValue("gpt-6-luna"));
    expect(screen.queryByText("Modèles enregistrés.")).not.toBeInTheDocument();
  });

  it("removing an override returns to tier", async () => {
    const { puts, user } = setup({ agent_overrides: { tutor: openai, scout: openai } });
    await showAdvanced(user);
    expect(provider("Tuteur")).toHaveValue("openai");
    expect(model("Tuteur")).toHaveValue("gpt-6-luna");

    await user.selectOptions(provider("Tuteur"), "Niveau par défaut (Standard)");
    expect(puts).toHaveLength(1);
    expect(puts[0]!.agent_overrides).toEqual({ scout: openai }); // seule celle du tuteur part
    expect(await screen.findByLabelText("Fournisseur (Tuteur)")).toHaveValue("");
    expect(screen.queryByLabelText("Modèle (Tuteur)")).not.toBeInTheDocument();
    expect(provider("Éclaireur")).toHaveValue("openai");
  });

  it("waits for the model of a provider without a list before saving anything", async () => {
    const { puts, user } = setup();
    await showAdvanced(user);
    await user.selectOptions(provider("Stratège"), "glm");
    expect(puts).toEqual([]);
    const field = model("Stratège");
    expect(field).toHaveValue("");
    await user.type(field, "glm-5.3{Enter}");
    await screen.findByDisplayValue("glm-5.3");
    expect(puts).toHaveLength(1);
    expect(puts[0]!.agent_overrides).toEqual({ strategist: { provider: "glm", model: "glm-5.3" } });
  });

  it("says an agent no longer exists when the server refuses the override, without echo", async () => {
    const { user } = setup({}, () => refusedFieldsResponse("agent_overrides"));
    await showAdvanced(user);
    await user.selectOptions(provider("Tuteur"), "openai");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Un des agents choisis n'existe plus : recharge la page, puis réessaie.",
    );
    expect(provider("Tuteur")).toHaveValue(""); // rien n'est affiché qui n'ait été enregistré
  });

  it("keeps an override of an agent the server no longer knows, so it can be removed", async () => {
    const { puts, user } = setup({ agent_overrides: { ghost_agent: openai } });
    await showAdvanced(user);
    expect(screen.getByText("Agent inconnu : rends-le au niveau par défaut.")).toBeInTheDocument();
    await user.selectOptions(provider("ghost_agent"), "Niveau par défaut");
    // une fois retirée, la ligne de l'agent inconnu disparaît
    await waitFor(() => expect(screen.queryByLabelText("Fournisseur (ghost_agent)")).toBeNull());
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
    await screen.findByRole("heading", { level: 1, name: "Modèles et clés" });
    await user.click(screen.getByRole("button", { name: "Afficher le mode avancé" }));
    expect(await screen.findByText("Panne des agents.")).toBeInTheDocument();
    fails = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    await screen.findByRole("table", { name: "Modèle par agent" });
  });
});
