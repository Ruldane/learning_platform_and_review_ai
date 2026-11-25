import { fireEvent, screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { closedGate, refusedFieldsResponse, settingsApi } from "@/test/settingsApi";
import { server } from "@/test/server";
import { settingsFixture } from "../../fixtures";
import { AvailabilityPage } from "./AvailabilityPage";

const overrides = { tutor: { provider: "openai", model: "gpt-6-luna" } };
const stored = {
  ...settingsFixture,
  agent_overrides: overrides,
  excluded_domains: ["pinterest.com"],
};

function setup(put?: Parameters<typeof settingsApi>[0]["put"], gate?: Promise<void>) {
  const api = settingsApi({ settings: stored, put, gate });
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/settings/availability", element: <AvailabilityPage /> }],
    "/settings/availability",
  );
  return { ...api, ...view };
}

const TITLE = "Availability and pace";
const SAVED = "Settings saved.";
const SECOND_FOLLOW_UP = "Second follow-up";
const WEEKEND_MIN = "Weekend block, minimum (minutes)";
const WEEKEND_MAX = "Weekend block, maximum (minutes)";
const LESSON_LANGUAGE = "Lesson language";
const DEBATE_ROUNDS = "Debate rounds";
const SESSION_CAP = "Cap per session (tokens)";
const weekday = () => screen.getByLabelText("Minutes per day, Monday to Friday");
const delay = (name: string) => screen.getByLabelText(name);
const save = () => screen.getByRole("button", { name: "Save" });

describe("AvailabilityPage", () => {
  it("availability saves and shows weekly budget", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: TITLE });
    expect(weekday()).toHaveValue(120);
    expect(screen.getByText("Weekly budget: 14 h")).toBeInTheDocument();

    await user.clear(weekday());
    await user.type(weekday(), "90");
    expect(screen.getByText("Weekly budget: 11 h 30")).toBeInTheDocument();
    await user.clear(screen.getByLabelText(WEEKEND_MAX));
    await user.type(screen.getByLabelText(WEEKEND_MAX), "300");
    expect(screen.getByText("Weekly budget: 12 h 30")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Brief time"), { target: { value: "06:45" } });
    await user.clear(screen.getByLabelText(DEBATE_ROUNDS));
    await user.type(screen.getByLabelText(DEBATE_ROUNDS), "4");
    await user.clear(screen.getByLabelText(SESSION_CAP));
    await user.type(screen.getByLabelText(SESSION_CAP), "200000");
    await user.selectOptions(screen.getByLabelText(LESSON_LANGUAGE), "en");
    expect(puts).toEqual([]); // rien n'est enregistré avant le bouton
    await user.click(save());

    expect(await screen.findByText(SAVED)).toBeInTheDocument();
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
    await screen.findByRole("heading", { level: 1, name: TITLE });
    await user.clear(delay(SECOND_FOLLOW_UP));
    await user.type(delay(SECOND_FOLLOW_UP), "7");
    expect(delay(SECOND_FOLLOW_UP)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(/^Error: Three strictly increasing numbers of days/)).toHaveClass(
      "text-destructive",
    );
    expect(save()).toHaveAttribute("aria-disabled", "true");

    await user.clear(delay(SECOND_FOLLOW_UP));
    await user.type(delay(SECOND_FOLLOW_UP), "30");
    expect(save()).toHaveAttribute("aria-disabled", "true"); // 7, 30, 21 : pas croissant
    await user.clear(delay("Third follow-up"));
    await user.type(delay("Third follow-up"), "45");
    expect(delay(SECOND_FOLLOW_UP)).toHaveAttribute("aria-invalid", "false");
    await user.click(save());
    await screen.findByText(SAVED);
    expect(puts[0]).toMatchObject({ reminder_delays_days: [7, 30, 45] });
  });

  it("blocks the save while a duration or the weekend block is out of order", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { level: 1, name: TITLE });
    await user.clear(screen.getByLabelText(WEEKEND_MIN));
    await user.type(screen.getByLabelText(WEEKEND_MIN), "500");
    expect(screen.getByText(/weekend minimum must stay less than or equal/)).toBeVisible();
    expect(save()).toHaveAttribute("aria-disabled", "true");
    await user.clear(weekday());
    await user.type(weekday(), "1500");
    expect(weekday()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Weekly budget: fix the durations above.")).toBeVisible();
    expect(puts).toEqual([]);
  });

  it("422 field error attached without echo", async () => {
    const { user } = setup(() => refusedFieldsResponse("availability.weekday_minutes"));
    await screen.findByRole("heading", { level: 1, name: TITLE });
    await user.clear(weekday());
    await user.type(weekday(), "777");
    await user.click(save());

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid request.");
    expect(weekday()).toHaveAttribute("aria-invalid", "true");
    expect(
      screen.getByText("Error: The server refused this value: check it."),
    ).toBeInTheDocument();
    // la valeur refusée n'est écrite nulle part dans la page (seulement dans le champ qu'on a
    // saisi)
    expect(document.body).not.toHaveTextContent("777");
    expect(weekday()).toHaveValue(777);
    expect(screen.getByLabelText(DEBATE_ROUNDS)).toHaveAttribute("aria-invalid", "false");
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
    await screen.findByRole("heading", { level: 1, name: TITLE });
    await user.clear(weekday());
    await user.type(weekday(), "45");
    await user.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    expect(weekday()).toHaveValue(45);
    expect(weekday()).toHaveAttribute("aria-invalid", "false");
  });

  it("keeps the focus on the save button after saving, a refusal and when blocked", async () => {
    const { user } = setup();
    await screen.findByRole("heading", { level: 1, name: TITLE });
    await user.click(save()); // rien à enregistrer : bloqué, le focus reste sur le bouton
    expect(save()).toHaveFocus();
    expect(save()).toHaveAccessibleDescription("Nothing to save.");
    await user.clear(weekday());
    await user.type(weekday(), "99");
    await user.click(save());
    await screen.findByText(SAVED);
    expect(save()).toHaveFocus();
    await user.clear(weekday());
    await user.type(weekday(), "1500");
    await user.click(save());
    expect(save()).toHaveFocus();
    expect(save()).toHaveAccessibleDescription("Fix the flagged fields before saving.");
  });

  it("keeps what is typed while the save is running", async () => {
    const held = closedGate();
    const { user, puts } = setup(undefined, held.promise);
    await screen.findByRole("heading", { level: 1, name: TITLE });
    await user.clear(weekday());
    await user.type(weekday(), "90");
    await user.click(save());
    await waitFor(() => expect(puts).toHaveLength(1)); // l'envoi est en cours, tenu par la porte
    await user.type(weekday(), "5"); // pendant l'envoi : 905
    held.open();
    await screen.findByText("Unsaved changes.");
    expect(puts[0]).toMatchObject({ availability: { weekday_minutes: 90 } });
    expect(weekday()).toHaveValue(905);
  });

  it("keeps a lesson language the list does not know", async () => {
    const api = settingsApi({ settings: { ...stored, lesson_language: "nl" } });
    server.use(...api.handlers);
    renderRoutes(
      [{ path: "/settings/availability", element: <AvailabilityPage /> }],
      "/settings/availability",
    );
    expect(await screen.findByLabelText(LESSON_LANGUAGE)).toHaveValue("nl");
  });
});
