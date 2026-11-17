import { fireEvent, screen } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { refusedFieldsResponse, settingsApi } from "@/test/settingsApi";
import { server } from "@/test/server";
import { settingsFixture } from "../../fixtures";
import { AvailabilityPage } from "./AvailabilityPage";

const overrides = { tutor: { provider: "openai", model: "gpt-6-luna" } };
const stored = {
  ...settingsFixture,
  agent_overrides: overrides,
  excluded_domains: ["pinterest.com"],
};

function setup(put?: Parameters<typeof settingsApi>[0]["put"]) {
  const api = settingsApi({ settings: stored, put });
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/reglages/disponibilite", element: <AvailabilityPage /> }],
    "/reglages/disponibilite",
  );
  return { ...api, ...view };
}

const weekday = () => screen.getByLabelText("Minutes par jour, du lundi au vendredi");
const delay = (name: string) => screen.getByLabelText(name);
const save = () => screen.getByRole("button", { name: "Enregistrer" });

describe("AvailabilityPage", () => {
  it("availability saves and shows weekly budget", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Disponibilité et rythme" });
    expect(weekday()).toHaveValue(120);
    expect(screen.getByText("Budget hebdomadaire : 14 h")).toBeInTheDocument();

    await user.clear(weekday());
    await user.type(weekday(), "90");
    expect(screen.getByText("Budget hebdomadaire : 11 h 30")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Bloc du week-end, maximum (minutes)"));
    await user.type(screen.getByLabelText("Bloc du week-end, maximum (minutes)"), "300");
    expect(screen.getByText("Budget hebdomadaire : 12 h 30")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Heure du brief"), { target: { value: "06:45" } });
    await user.clear(screen.getByLabelText("Tours de débat"));
    await user.type(screen.getByLabelText("Tours de débat"), "4");
    await user.clear(screen.getByLabelText("Plafond par session (jetons)"));
    await user.type(screen.getByLabelText("Plafond par session (jetons)"), "200000");
    await user.selectOptions(screen.getByLabelText("Langue des leçons"), "en");
    expect(puts).toEqual([]); // rien n'est enregistré avant le bouton
    await user.click(save());

    expect(await screen.findByText("Réglages enregistrés.")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      availability: {
        weekday_minutes: 90,
        weekend_block_min_minutes: 180,
        weekend_block_max_minutes: 300,
      },
      brief_time: "06:45",
      debate_rounds: 4,
      session_token_cap: 200000,
      lesson_language: "en",
      reminder_delays_days: [7, 14, 21],
      // le reste des réglages est repris tel quel, dont ceux d'une autre page
      onboarding_done: true,
      agent_overrides: overrides,
      excluded_domains: ["pinterest.com"],
      tiers: settingsFixture.tiers,
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");
    expect(puts[0]!.availability).not.toHaveProperty("weekly_budget_minutes");
  });

  it("delays must increase", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Disponibilité et rythme" });
    await user.clear(delay("Deuxième relance"));
    await user.type(delay("Deuxième relance"), "7");
    expect(delay("Deuxième relance")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(/strictement croissants/)).toHaveClass("text-destructive");
    expect(save()).toHaveAttribute("aria-disabled", "true");

    await user.clear(delay("Deuxième relance"));
    await user.type(delay("Deuxième relance"), "30");
    expect(save()).toHaveAttribute("aria-disabled", "true"); // 7, 30, 21 : pas croissant
    await user.clear(delay("Troisième relance"));
    await user.type(delay("Troisième relance"), "45");
    expect(delay("Deuxième relance")).toHaveAttribute("aria-invalid", "false");
    await user.click(save());
    await screen.findByText("Réglages enregistrés.");
    expect(puts[0]).toMatchObject({ reminder_delays_days: [7, 30, 45] });
  });

  it("blocks the save while a duration or the weekend block is out of order", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: "Disponibilité et rythme" });
    await user.clear(screen.getByLabelText("Bloc du week-end, minimum (minutes)"));
    await user.type(screen.getByLabelText("Bloc du week-end, minimum (minutes)"), "500");
    expect(screen.getByText("Le minimum du week-end ne dépasse pas son maximum.")).toBeVisible();
    expect(save()).toHaveAttribute("aria-disabled", "true");
    await user.clear(weekday());
    await user.type(weekday(), "1500");
    expect(weekday()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Budget hebdomadaire : corrige les durées ci-dessus.")).toBeVisible();
    expect(puts).toEqual([]);
  });

  it("422 field error attached without echo", async () => {
    const { user } = setup(() => refusedFieldsResponse("availability.weekday_minutes"));
    await screen.findByRole("heading", { level: 1, name: "Disponibilité et rythme" });
    await user.clear(weekday());
    await user.type(weekday(), "777");
    await user.click(save());

    expect(await screen.findByRole("alert")).toHaveTextContent("Requête invalide");
    expect(weekday()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Le serveur a refusé cette valeur : vérifie-la.")).toBeInTheDocument();
    // la valeur refusée n'est écrite nulle part dans la page (seulement dans le champ qu'on a saisi)
    expect(document.body).not.toHaveTextContent("777");
    expect(weekday()).toHaveValue(777);
    expect(screen.getByLabelText("Tours de débat")).toHaveAttribute("aria-invalid", "false");
    // corriger le champ efface le refus
    await user.clear(weekday());
    await user.type(weekday(), "100");
    expect(weekday()).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps the typed values and shows the message when the save fails otherwise", async () => {
    const { user } = setup(() =>
      HttpResponse.json(
        { error: { code: "boom", message: "Panne du serveur.", details: null } },
        { status: 500 },
      ),
    );
    await screen.findByRole("heading", { level: 1, name: "Disponibilité et rythme" });
    await user.clear(weekday());
    await user.type(weekday(), "45");
    await user.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    expect(weekday()).toHaveValue(45);
    expect(weekday()).toHaveAttribute("aria-invalid", "false");
  });

  it("keeps a lesson language the list does not know", async () => {
    const api = settingsApi({ settings: { ...stored, lesson_language: "nl" } });
    server.use(...api.handlers);
    renderRoutes(
      [{ path: "/reglages/disponibilite", element: <AvailabilityPage /> }],
      "/reglages/disponibilite",
    );
    expect(await screen.findByLabelText("Langue des leçons")).toHaveValue("nl");
  });
});
