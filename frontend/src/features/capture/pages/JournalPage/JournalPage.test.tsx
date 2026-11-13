import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { entryOut } from "@/test/captureApi";
import { API } from "@/test/councilApi";
import { apiError } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { useCaptureDialog } from "../../captureDialog";
import { JournalPage } from "./JournalPage";

type Page = { entries: Record<string, unknown>[]; next_before: string | null };

/** Sert `pages` l'une après l'autre ; garde les paramètres de chaque requête. */
function setup(pages: Page[], reply?: () => Response) {
  const queries: URLSearchParams[] = [];
  server.use(
    http.get(`${API}/journal`, ({ request }) => {
      queries.push(new URL(request.url).searchParams);
      if (reply) return reply();
      const index = Math.min(queries.length - 1, pages.length - 1);
      return HttpResponse.json(pages[index]);
    }),
  );
  render(
    <MemoryRouter>
      <JournalPage />
    </MemoryRouter>,
    { wrapper: createQueryWrapper() },
  );
  return { queries, user: userEvent.setup() };
}

afterEach(() => useCaptureDialog.setState({ open: false, sessionId: null }));

describe("JournalPage", () => {
  it("lists journal entries by week with weekly reviews", async () => {
    setup([
      {
        entries: [
          entryOut("e1", { occurred_on: "2026-11-24", text: "Note de mardi" }),
          entryOut("e2", {
            occurred_on: "2026-11-23",
            kind: "weekly_review",
            text: "Bilan : 5 tâches faites",
          }),
          entryOut("e3", {
            occurred_on: "2026-11-17",
            kind: "study_session",
            text: "Session sur REST",
            links: {
              session_id: null,
              study_session_id: "st1",
              quiz_attempt_id: null,
              memory_item_id: null,
            },
          }),
        ],
        next_before: null,
      },
    ]);
    const weeks = await screen.findAllByRole("heading", { level: 2 });
    expect(weeks.map((week) => week.textContent)).toEqual([
      "Semaine du lundi 23 novembre",
      "Semaine du lundi 16 novembre",
    ]);
    const first = within(weeks[0]!.closest("section")!).getAllByRole("listitem");
    expect(within(first[0]!).getByText("Bilan hebdomadaire")).toBeInTheDocument();
    expect(within(first[1]!).getByText("Note de mardi")).toBeInTheDocument();
    const second = within(weeks[1]!.closest("section")!);
    expect(second.getByRole("link", { name: "Voir la session" })).toHaveAttribute(
      "href",
      "/etudier/session/st1",
    );
  });

  it("filters by type and reads the journal again for that type", async () => {
    const { queries, user } = setup([{ entries: [entryOut("e1")], next_before: null }]);
    await screen.findByText("Entrée e1");
    await user.selectOptions(screen.getByLabelText("Type d'entrée"), "quiz");
    await waitFor(() => expect(queries.some((query) => query.get("kind") === "quiz")).toBe(true));
  });

  it("keeps the filter and its focus while the new type loads (revue finale 5, C-m2)", async () => {
    const { user } = setup([
      { entries: [entryOut("e1")], next_before: null },
      { entries: [entryOut("e2", { kind: "quiz", text: "Quiz réussi" })], next_before: null },
    ]);
    await screen.findByText("Entrée e1");
    const filter = screen.getByLabelText("Type d'entrée");
    filter.focus();
    await user.selectOptions(filter, "quiz");
    // Pendant la lecture du nouveau type, la liste n'est pas démontée : le focus reste au filtre.
    expect(screen.getByLabelText("Type d'entrée")).toBe(filter);
    expect(filter).toHaveFocus();
    expect(await screen.findByText("Quiz réussi")).toBeInTheDocument();
    expect(filter).toHaveFocus();
  });

  it("loads the next page from next_before", async () => {
    const { queries, user } = setup([
      { entries: [entryOut("e1", { occurred_on: "2026-11-24" })], next_before: "e1" },
      {
        entries: [entryOut("e2", { occurred_on: "2026-11-10", text: "Plus ancienne" })],
        next_before: null,
      },
    ]);
    await screen.findByText("Entrée e1");
    await user.click(screen.getByRole("button", { name: "Voir les entrées plus anciennes" }));
    expect(await screen.findByText("Plus ancienne")).toBeInTheDocument();
    expect(queries[1]?.get("before")).toBe("e1");
    expect(screen.queryByRole("button", { name: "Voir les entrées plus anciennes" })).toBeNull();
  });

  it("shows an empty state that opens the capture", async () => {
    const { user } = setup([{ entries: [], next_before: null }]);
    expect(await screen.findByText("Ton journal est vide")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Capturer une note" }));
    expect(useCaptureDialog.getState().open).toBe(true);
  });

  it("shows loading, then a retryable error", async () => {
    let failing = true;
    const { user } = setup([{ entries: [], next_before: null }], () =>
      failing
        ? HttpResponse.json(apiError("internal_error", "Panne du serveur."), { status: 500 })
        : HttpResponse.json({ entries: [entryOut("e1")], next_before: null }),
    );
    expect(screen.getByText("Chargement du journal…")).toBeInTheDocument();
    expect(await screen.findByText("Panne du serveur.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Entrée e1")).toBeInTheDocument();
  });
});
