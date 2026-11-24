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

const DELETED = "Your data has been deleted: Tremplin is starting from scratch.";

describe("WelcomePage", () => {
  it("five steps in order with step counter", async () => {
    const { user } = setup();
    for (const [index, name] of TITLES.entries()) {
      const heading = await title(name);
      await waitFor(() => expect(heading).toHaveFocus());
      expect(screen.getByText(`Step ${index + 1} of 5`)).toBeInTheDocument();
      if (index === 0) expect(screen.queryByRole("button", { name: "Previous" })).toBeNull();
      if (index < 4) await user.click(next());
    }
    // Le dernier bouton termine ; « Précédent » revient d'une étape.
    expect(finish()).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Previous" }));
    const back = await title(TITLES[3]!);
    await waitFor(() => expect(back).toHaveFocus());
    expect(screen.getByText("Step 4 of 5")).toBeInTheDocument();
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
    const list = await screen.findByRole("list", { name: "Service status" });
    expect(within(list).getByText("Database : responding")).toBeInTheDocument();
    expect(within(list).getByText(/Vector memory \(Qdrant\) : not responding/)).toBeVisible();
    expect(await screen.findByText("bge-m3: 42%")).toBeInTheDocument();
    await user.click(next());
    await title(TITLES[1]!);
  });

  it("says the data are gone when it comes after « Tout supprimer »", async () => {
    const { router } = setup();
    await title(TITLES[0]!);
    expect(screen.queryByText(DELETED)).toBeNull();
    await router.navigate("/welcome", { state: { deleted: true }, replace: true });
    expect(await screen.findByText(DELETED)).toBeVisible();
  });

  it("puts the arrival message into a zone that was already in the page", async () => {
    const records: MutationRecord[] = [];
    const observer = new MutationObserver((batch) => records.push(...batch));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    setup({}, { deleted: true });
    const notice = await screen.findByTestId("welcome-notice");
    await screen.findByText(DELETED);
    records.push(...observer.takeRecords());
    observer.disconnect();
    expect(notice).toHaveAttribute("role", "status");
    // le texte est venu dans la zone déjà montée, pas avec elle
    expect(records.some((record) => record.target === notice && record.addedNodes.length > 0)).toBe(
      true,
    );
  });

  it("keeps that zone empty when nothing was deleted", async () => {
    setup();
    await title(TITLES[0]!);
    expect(screen.getByTestId("welcome-notice")).toBeEmptyDOMElement();
  });

  it("step 2 explains what leaves the machine, before any key is asked", async () => {
    const { user } = setup();
    await goTo(user, 2);
    expect(screen.getByRole("table", { name: "What leaves your machine" })).toBeInTheDocument();
    expect(screen.getByText(/removes your name, email and phone number/)).toBeInTheDocument();
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
    expect(screen.getByText("Weekly budget: 11 h 30")).toBeInTheDocument();
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
    expect(finish()).toHaveAccessibleDescription("Fix the flagged fields before finishing.");
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
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid request.");
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
    expect(await screen.findByText("Language model key : to set up in step 3")).toBeVisible();
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
