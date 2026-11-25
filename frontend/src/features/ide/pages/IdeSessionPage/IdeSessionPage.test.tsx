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
    await user.click(screen.getByText("Prompt"));
    expect(screen.getByText("Écris une fonction add(a, b).")).toBeVisible();
  });

  it("falls back to the session title for a free session", async () => {
    renderSession({ exercises: [], session: { title: "Brouillon", exercise_id: null } });
    expect(await screen.findByRole("heading", { level: 1, name: "Brouillon" })).toBeInTheDocument();
  });

  it("says when the session passed", async () => {
    renderSession({ session: { passed: true } });
    expect(await screen.findByText("Passed")).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("switches between the files of the session", async () => {
    const { user } = renderSession({
      session: { files: { "main.py": "a = 1\n", "util.py": "b = 2\n" } },
    });
    const editor = await findEditor();
    expect(editor).toHaveValue("a = 1\n");
    const files = screen.getByRole("navigation", { name: "Session files" });
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
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(calls.teach).toHaveLength(0);
  });

  it("changes the teacher mode and keeps the caps the server gave", async () => {
    const { user, calls } = renderSession({ preferences: { session_cap: 5000, day_cap: 9000 } });
    const auto = await screen.findByRole("switch", {
      name: "The professor steps in on its own after an error",
    });
    await user.click(auto);
    await waitFor(() => expect(calls.prefs).toHaveLength(1));
    expect(calls.prefs[0]).toEqual({
      teacher_mode: "on_demand",
      idle_trigger: false,
      teacher_style: "guide",
      mcp_can_write_files: false,
      session_cap: 5000,
      day_cap: 9000,
    });
    await waitFor(() => expect(auto).not.toBeChecked());
  });

  it("switches the teacher between guide and pair and keeps the other settings", async () => {
    const { user, calls } = renderSession({ preferences: { session_cap: 5000, day_cap: 9000 } });
    await user.click(await screen.findByRole("radio", { name: /Pair/ }));
    await waitFor(() => expect(calls.prefs).toHaveLength(1));
    expect(calls.prefs[0]).toEqual({
      teacher_mode: "auto",
      idle_trigger: false,
      teacher_style: "pair",
      mcp_can_write_files: false,
      session_cap: 5000,
      day_cap: 9000,
    });
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
    await user.click(screen.getByRole("button", { name: /^Run code/ }));
    const alert = await screen.findByRole("alert", {}, { timeout: MAX_FAILURES * 400 + 2000 });
    expect(alert).toHaveTextContent("The output could not be reloaded.");
    expect(screen.getByText("The sandbox could not run the code.")).toBeInTheDocument();
  });
});
