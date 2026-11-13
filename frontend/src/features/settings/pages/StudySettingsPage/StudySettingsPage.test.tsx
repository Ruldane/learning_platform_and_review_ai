import { fireEvent, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { settingsFixture } from "../../fixtures";
import { StudySettingsPage } from "./StudySettingsPage";

const API = `${apiBaseUrl}/api/v1`;
const stored = {
  ...settingsFixture,
  excluded_domains: ["pinterest.com"],
  availability: { ...settingsFixture.availability!, weekday_minutes: 90 },
};

function setup(options: { get?: () => Response; put?: (body: unknown) => Response } = {}) {
  const puts: unknown[] = [];
  server.use(
    http.get(`${API}/settings`, () => options.get?.() ?? HttpResponse.json(stored)),
    http.put(`${API}/settings`, async ({ request }) => {
      const body = await request.json();
      puts.push(body);
      return options.put?.(body) ?? HttpResponse.json({ ...stored, ...(body as object) });
    }),
  );
  const view = renderRoutes(
    [{ path: "/reglages/etude", element: <StudySettingsPage /> }],
    "/reglages/etude",
  );
  return { puts, ...view };
}

const work = () => screen.getByLabelText("Durée de travail (minutes)");
const pause = () => screen.getByLabelText("Durée de pause (minutes)");

describe("StudySettingsPage", () => {
  it("saves study rhythm and timezone with a full PUT", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { name: "Étude et bilan" });
    expect(work()).toHaveValue(50);
    expect(pause()).toHaveValue(10);
    await user.clear(work());
    await user.type(work(), "45");
    await user.clear(pause());
    await user.type(pause(), "5");
    await user.selectOptions(screen.getByLabelText("Jour du bilan"), "monday");
    fireEvent.change(screen.getByLabelText("Heure du bilan"), { target: { value: "19:30" } });
    await user.selectOptions(screen.getByLabelText("Fuseau horaire"), "America/New_York");
    expect(puts).toEqual([]); // rien n'est enregistré avant le bouton
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(await screen.findByText("Réglages enregistrés.")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({
      study_work_minutes: 45,
      study_break_minutes: 5,
      weekly_review: { day: "monday", time: "19:30" },
      timezone: "America/New_York",
      // le reste des réglages est repris tel quel
      excluded_domains: ["pinterest.com"],
      tiers: settingsFixture.tiers,
      availability: { weekday_minutes: 90 },
      brief_time: "07:00",
      search_max_queries: 12,
    });
    expect(puts[0]).not.toHaveProperty("vision_enabled");
  });

  it("offers the timezones of the browser, with the saved one even if unknown to it", async () => {
    server.use(
      http.get(`${API}/settings`, () => HttpResponse.json({ ...stored, timezone: "Etc/Zoulou" })),
    );
    renderRoutes([{ path: "/reglages/etude", element: <StudySettingsPage /> }], "/reglages/etude");
    const zone = await screen.findByLabelText("Fuseau horaire");
    expect(zone).toHaveValue("Etc/Zoulou");
    expect(screen.getByRole("option", { name: "Europe/Paris" })).toBeInTheDocument();
  });

  it("blocks the save while a duration is outside the limits of the contract", async () => {
    const { puts, user } = setup();
    await screen.findByRole("heading", { name: "Étude et bilan" });
    await user.clear(work());
    await user.type(work(), "5");
    expect(work()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
    await user.clear(work());
    await user.type(work(), "121");
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
    await user.clear(work());
    await user.type(work(), "60");
    await user.clear(pause());
    await user.type(pause(), "0");
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeEnabled();
    expect(puts).toEqual([]);
  });

  it("keeps the typed values and shows the message when the save fails", async () => {
    const { user } = setup({
      put: () =>
        HttpResponse.json(
          { error: { code: "invalid_settings", message: "Réglages refusés.", details: null } },
          { status: 422 },
        ),
    });
    await screen.findByRole("heading", { name: "Étude et bilan" });
    await user.clear(work());
    await user.type(work(), "45");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Réglages refusés.");
    expect(work()).toHaveValue(45);
  });

  it("announces the loading, then shows an error with a retry button", async () => {
    let calls = 0;
    const { user } = setup({
      get: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(
              { error: { code: "boom", message: "Panne du serveur.", details: null } },
              { status: 500 },
            )
          : HttpResponse.json(stored);
      },
    });
    expect(screen.getByRole("status")).toHaveTextContent("Chargement des réglages d'étude…");
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Étude et bilan" })).toBeInTheDocument();
  });
});
