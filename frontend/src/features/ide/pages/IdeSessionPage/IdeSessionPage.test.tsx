import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { errorBody } from "@/test/authApi";
import { API } from "@/test/councilApi";
import { AUTOSAVE_MS } from "../../hooks/useFilesDraft";
import { MAX_FAILURES } from "../../hooks/useRunPolling";
import { findEditor, renderSession } from "../../ideTestkit";

describe("IdeSessionPage", () => {
  it("shows the exercise title and its statement on demand", async () => {
    const { user } = renderSession({ session: { title: "Séance 1" } });
    await findEditor();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Additionner" }),
    ).toBeInTheDocument();
    await user.click(screen.getByText("Énoncé"));
    expect(screen.getByText("Écris une fonction add(a, b).")).toBeVisible();
  });

  it("falls back to the session title for a free session", async () => {
    renderSession({ exercises: [], session: { title: "Brouillon", exercise_id: null } });
    expect(await screen.findByRole("heading", { level: 1, name: "Brouillon" })).toBeInTheDocument();
  });

  it("says when the session passed", async () => {
    renderSession({ session: { passed: true } });
    expect(await screen.findByText("Réussie")).toBeInTheDocument();
  });

  it("shows a readable error when the session cannot be read, and retries", async () => {
    renderSession({
      override: [
        http.get(`${API}/ide/sessions/s1`, () =>
          HttpResponse.json(errorBody("not_found", "Séance introuvable."), { status: 404 }),
        ),
      ],
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Séance introuvable.");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });

  it("switches between the files of the session", async () => {
    const { user } = renderSession({
      session: { files: { "main.py": "a = 1\n", "util.py": "b = 2\n" } },
    });
    const editor = await findEditor();
    expect(editor).toHaveValue("a = 1\n");
    const files = screen.getByRole("navigation", { name: "Fichiers de la séance" });
    await user.click(within(files).getByRole("button", { name: "util.py" }));
    expect(editor).toHaveValue("b = 2\n");
    expect(within(files).getByRole("button", { name: "util.py" })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("saves by itself after a pause in typing, and asks the teacher nothing", async () => {
    const { user, calls } = renderSession();
    const editor = await findEditor();
    await user.type(editor, "y");
    expect(calls.puts).toHaveLength(0);
    await waitFor(() => expect(calls.puts).toHaveLength(1), { timeout: AUTOSAVE_MS + 2000 });
    expect(await screen.findByText("Enregistré")).toBeInTheDocument();
    expect(calls.teach).toHaveLength(0);
  });

  it("changes the teacher mode and keeps the caps the server gave", async () => {
    const { user, calls } = renderSession({ preferences: { session_cap: 5000, day_cap: 9000 } });
    const auto = await screen.findByRole("switch", {
      name: "Le professeur intervient tout seul après une erreur",
    });
    await user.click(auto);
    await waitFor(() => expect(calls.prefs).toHaveLength(1));
    expect(calls.prefs[0]).toEqual({
      teacher_mode: "on_demand",
      idle_trigger: false,
      session_cap: 5000,
      day_cap: 9000,
    });
    await waitFor(() => expect(auto).not.toBeChecked());
  });

  it("stops reading the output after repeated failures and says so", async () => {
    const { user } = renderSession({
      override: [
        http.get(`${API}/ide/runs/r1`, () =>
          HttpResponse.json(errorBody("boom", "Le serveur ne répond pas."), { status: 500 }),
        ),
      ],
    });
    await findEditor();
    await user.click(screen.getByRole("button", { name: /^Exécuter/ }));
    const alert = await screen.findByRole("alert", {}, { timeout: MAX_FAILURES * 400 + 2000 });
    expect(alert).toHaveTextContent("La sortie n'a pas pu être relue.");
    expect(screen.getByText("Le bac à sable n'a pas pu exécuter le code.")).toBeInTheDocument();
  });
});
