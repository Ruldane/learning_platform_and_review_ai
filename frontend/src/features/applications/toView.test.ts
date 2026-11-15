import { describe, expect, it } from "vitest";
import { alertOut, applicationOut, detailOut, eventOut, reminderOut } from "@/test/applicationsApi";
import {
  toAlertView,
  toApplicationView,
  toConfirmationView,
  toContactsIn,
  toEventView,
  toReminderView,
  toStatsView,
} from "./toView";
import type { ApplicationDetail, ApplicationOut, ApplicationStatsOut } from "./types";

describe("toView", () => {
  it("turns a list row into the card shape, from the list or from the detail", () => {
    const view = {
      id: "a1",
      company: "Acme",
      title: "Data engineer",
      status: "applied",
      channel: "linkedin",
      appliedOn: "2026-11-03",
      interviewOn: null,
      nextAction: "Relancer",
      nextActionOn: "2026-11-20",
      dueReminders: 1,
    };
    expect(toApplicationView(applicationOut() as ApplicationOut)).toEqual(view);
    expect(toApplicationView(detailOut() as unknown as ApplicationDetail)).toEqual(view);
  });

  it("keeps the reminder without its channel, with its contact", () => {
    const view = toReminderView(reminderOut() as never);
    expect(view).toEqual({
      id: "r1",
      applicationId: "a1",
      kind: "linkedin_7",
      dueOn: "2026-11-10",
      company: "Acme",
      title: "Data engineer",
      contact: { id: "c1", name: "Camille Durand", role: "Responsable data", url: null },
      linkedinSearchUrl: null,
      draft: "Bonjour Camille, je me permets de revenir vers vous.",
    });
    expect(view).not.toHaveProperty("channel");
  });

  it("turns an event", () => {
    expect(
      toEventView(
        eventOut({ kind: "status", status_from: "to_apply", status_to: "applied" }) as never,
      ),
    ).toMatchObject({
      kind: "status",
      statusFrom: "to_apply",
      statusTo: "applied",
    });
  });

  it("always gives the eight statuses, at zero when the server says nothing", () => {
    const stats = toStatsView({
      by_status: { applied: 2 },
      due_reminders: 1,
      mean_response_days: null,
      response_rate: null,
    } as ApplicationStatsOut);
    expect(Object.keys(stats.byStatus)).toHaveLength(8);
    expect(stats.byStatus).toMatchObject({ to_apply: 0, applied: 2, withdrawn: 0 });
    expect(stats).toMatchObject({ dueReminders: 1, meanResponseDays: null, responseRate: null });
  });

  it("maps an alert field by field", () => {
    expect(toAlertView(alertOut() as never)).toEqual({
      level: "probable",
      applicationId: "a9",
      company: "Acme",
      title: "Data engineer",
      status: "applied",
      message: "Attention, tu as déjà une fiche chez Acme pour le poste Data engineer.",
    });
  });

  it("sends contacts without ids, trimmed, with empty role and link as null", () => {
    expect(
      toContactsIn([
        { id: "c1", name: " Camille ", role: "  ", url: null },
        { id: "", name: "Sam", role: "RH", url: " https://example.org/sam " },
      ]),
    ).toEqual([
      { name: "Camille", role: null, url: null },
      { name: "Sam", role: "RH", url: "https://example.org/sam" },
    ]);
  });

  it("reads the confirmation question: values, limits, required and the server's choices", () => {
    const view = toConfirmationView({
      interrupt_id: "q1",
      kind: "application_confirm",
      question: "Je crée cette fiche ?",
      options: [{ value: "create", label: "Créer la fiche" }],
      fields: [
        { id: "company", label: "Entreprise", required: true, max_length: 200, value: "Acme" },
        { id: "notes", label: "Notes", required: false, max_length: 500 },
      ],
    });
    expect(view).toEqual({
      question: "Je crée cette fiche ?",
      options: [{ value: "create", label: "Créer la fiche" }],
      fields: [
        { id: "company", label: "Entreprise", required: true, maxLength: 200, value: "Acme" },
        { id: "notes", label: "Notes", required: false, maxLength: 500, value: "" },
      ],
    });
  });
});
