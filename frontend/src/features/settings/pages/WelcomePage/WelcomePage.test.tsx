import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { embeddingOut, healthReport } from "@/test/onboardingApi";
import { closedGate, refusedFieldsResponse } from "@/test/settingsApi";
import { settingsFixture } from "../../fixtures";
import {
  field,
  finish,
  fresh,
  goTo,
  next,
  setup,
  skipAll,
  TITLES,
  title,
  WEEKDAY,
} from "./welcomeTestkit";

describe("WelcomePage", () => {
  it("five steps in order with step counter", async () => {
    const { user } = setup();
    for (const [index, name] of TITLES.entries()) {
      const heading = await title(name);
      await waitFor(() => expect(heading).toHaveFocus());
      expect(screen.getByText(`Étape ${index + 1} sur 5`)).toBeInTheDocument();
      if (index === 0) expect(screen.queryByRole("button", { name: "Précédent" })).toBeNull();
      if (index < 4) await user.click(next());
    }
    // Le dernier bouton termine ; « Précédent » revient d'une étape.
    expect(finish()).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Précédent" }));
    const back = await title(TITLES[3]!);
    await waitFor(() => expect(back).toHaveFocus());
    expect(screen.getByText("Étape 4 sur 5")).toBeInTheDocument();
  });

  it("step 1 writes the state of each service and the progress of the model", async () => {
    const { user } = setup({
      health: [
        healthReport(
          { db: [true, "Disponible."], qdrant: [false, "Qdrant ne répond pas."] },
          "degraded",
        ),
      ],
      embedding: [embeddingOut(42)],
    });
    const list = await screen.findByRole("list", { name: "État des services" });
    expect(within(list).getByText(/Base de données : répond/)).toBeInTheDocument();
    expect(within(list).getByText(/Mémoire vectorielle \(Qdrant\) : ne répond pas/)).toBeVisible();
    expect(await screen.findByText("bge-m3 : 42 %")).toBeInTheDocument();
    await user.click(next());
    await title(TITLES[1]!);
  });

  it("step 2 explains what leaves the machine, before any key is asked", async () => {
    const { user } = setup();
    await goTo(user, 2);
    expect(screen.getByRole("table", { name: "Ce qui sort de ta machine" })).toBeInTheDocument();
    expect(screen.getByText(/retire ton nom, ton e-mail et ton téléphone/)).toBeInTheDocument();
  });

  it("finish saves availability and onboarding_done", async () => {
    const override = { provider: "openai", model: "gpt-6-luna" };
    const { user, puts, router } = setup({
      settings: { ...fresh, agent_overrides: { tutor: override } },
    });
    await goTo(user, 5);
    const weekday = field(WEEKDAY);
    expect(weekday).toHaveValue(120);
    await user.clear(weekday);
    await user.type(weekday, "90");
    expect(screen.getByText("Budget hebdomadaire : 11 h 30")).toBeInTheDocument();
    await user.click(finish());
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      onboarding_done: true,
      availability: {
        weekday_minutes: 90,
        weekend_block_min_minutes: 180,
        weekend_block_max_minutes: 240,
      },
      agent_overrides: { tutor: override },
      tiers: settingsFixture.tiers,
      brief_time: "07:00",
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");
  });

  it("finish is blocked while a duration is out of bounds, and says why", async () => {
    const { user, puts } = setup();
    await goTo(user, 5);
    const weekday = field(WEEKDAY);
    await user.clear(weekday);
    await user.type(weekday, "2000");
    expect(finish()).toHaveAttribute("aria-disabled", "true");
    expect(finish()).toHaveAccessibleDescription("Corrige les champs signalés avant de terminer.");
    await user.click(finish());
    expect(puts).toEqual([]);
    expect(screen.getByRole("heading", { level: 1, name: TITLES[4]! })).toBeInTheDocument();
  });

  it("finish shows a refusal without the value, keeps the page, and can be retried", async () => {
    let calls = 0;
    const { user, puts } = setup({
      put: () =>
        ++calls === 1 ? refusedFieldsResponse("availability.weekday_minutes") : undefined,
    });
    await goTo(user, 5);
    await user.click(finish());
    expect(await screen.findByRole("alert")).toHaveTextContent("Requête invalide");
    expect(field(WEEKDAY)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("heading", { level: 1, name: TITLES[4]! })).toBeInTheDocument();
    await user.click(finish());
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(puts).toHaveLength(2);
  });

  it("skip link finishes without changing availability, from any step", async () => {
    const { user, puts, router } = setup();
    await goTo(user, 5);
    const weekday = field(WEEKDAY);
    await user.clear(weekday);
    await user.type(weekday, "90");
    await user.click(skipAll());
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      onboarding_done: true,
      availability: {
        weekday_minutes: 120,
        weekend_block_min_minutes: 180,
        weekend_block_max_minutes: 240,
      },
    });
  });

  it("skip link works on the first step, and ignores a second click while saving", async () => {
    const held = closedGate();
    const { user, puts } = setup({ gate: held.promise });
    await title(TITLES[0]!);
    await user.click(skipAll());
    await user.click(skipAll());
    held.open();
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
  });

  it("onboarding never shown again after finish", async () => {
    const { user, router } = setup();
    await goTo(user, 5);
    await user.click(finish());
    await screen.findByText("Accueil de Tremplin");
    await router.navigate("/reglages");
    expect(await screen.findByText("Réglages")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/reglages");
    await router.navigate("/");
    expect(await screen.findByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });

  it("works for a space with nothing set (after « Tout supprimer »)", async () => {
    const { user, puts } = setup({
      settings: { ...fresh, availability: null },
      health: [healthReport({ llm: [false, "Aucune clé"] }, "degraded")],
    });
    expect(await screen.findByText(/Clé d'un modèle de langage : à configurer/)).toBeVisible();
    await goTo(user, 5);
    expect(field(WEEKDAY)).toHaveValue(120);
    await user.click(finish());
    await screen.findByText("Accueil de Tremplin");
    expect(puts[0]).toMatchObject({
      onboarding_done: true,
      availability: {
        weekday_minutes: 120,
        weekend_block_min_minutes: 180,
        weekend_block_max_minutes: 240,
      },
    });
  });
});
