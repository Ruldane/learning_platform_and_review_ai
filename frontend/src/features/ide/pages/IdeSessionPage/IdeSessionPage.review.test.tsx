import { focusManager } from "@tanstack/react-query";
import { act, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { progress, runOut, sessionOut } from "@/test/ideApi";
import { AUTOSAVE_MS } from "../../hooks/useFilesDraft";
import { findEditor, refresh, renderSession, settle } from "../../ideTestkit";

type Options = NonNullable<Parameters<typeof renderSession>[0]>;

afterEach(() => focusManager.setFocused(undefined));

describe("IdeSessionPage, review fixes", () => {
  it("says a check run by Claude passed but does not count it", async () => {
    const options: Options = { reads: [progress({ id: "rc1", output: "1 passed\n" })] };
    const { calls } = renderSession(options);
    await findEditor();
    await waitFor(() => expect(calls.runListReads).toBe(1)); // la liste d'ouverture est lue
    options.runs = [runOut({ kind: "check" })];
    await refresh();
    expect(
      await screen.findByText("Tests réussis (exécution de Claude, non comptée)"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Vérification réussie/)).toBeNull();
  });

  it("a check of your own is counted as before", async () => {
    const { user } = renderSession();
    await findEditor();
    await user.click(screen.getByRole("button", { name: "Vérifier" }));
    expect(await screen.findByText(/Vérification réussie/)).toBeInTheDocument();
  });

  it("stops reading a run while the tab is hidden and goes on when it is back", async () => {
    const running = { status: "running", exit_code: null, duration_ms: null };
    const { user, calls } = renderSession({
      reads: [progress({ ...running, output: "a", next_offset: 1 }), progress({ output: "b" })],
    });
    await findEditor();
    await user.click(screen.getByRole("button", { name: /^Exécuter/ }));
    await waitFor(() => expect(calls.reads).toHaveLength(1));
    act(() => focusManager.setFocused(false));
    await settle(1000);
    expect(calls.reads).toHaveLength(1);
    act(() => focusManager.setFocused(true));
    expect(await screen.findByText(/Terminé \(code 0/)).toBeInTheDocument();
  });

  it("a setting changed in another tab is not undone by changing another one here", async () => {
    const options: Options = { preferences: { mcp_can_write_files: false } };
    const { user, calls } = renderSession(options);
    const auto = await screen.findByRole("switch", {
      name: "Le professeur intervient tout seul après une erreur",
    });
    options.preferences = { mcp_can_write_files: true, session_cap: 7000 }; // l'autre onglet
    await user.click(auto);
    await waitFor(() => expect(calls.prefs).toHaveLength(1));
    expect(calls.prefs[0]).toMatchObject({
      teacher_mode: "on_demand",
      mcp_can_write_files: true,
      session_cap: 7000,
    });
  });

  it("« Prendre celle de Claude » asks first, and « Annuler » keeps your edits", async () => {
    const options: Options = { session: { files: { "main.py": "a = 1\n" } } };
    const { user, calls } = renderSession(options);
    const editor = await findEditor();
    await user.type(editor, "b");
    options.session = { files: { "main.py": "a = 2\n" } };
    await refresh();
    const card = await screen.findByRole("alert", { name: /pendant que tu écrivais/ });
    await user.click(within(card).getByRole("button", { name: "Voir la version de Claude" }));
    await user.click(within(card).getByRole("button", { name: "Prendre celle de Claude" }));
    expect(within(card).getByText(/Tes retouches de main.py seront perdues/)).toBeInTheDocument();
    expect(editor).toHaveValue("a = 1\nb");
    await user.click(within(card).getByRole("button", { name: "Annuler" }));
    expect(within(card).getByRole("button", { name: "Prendre celle de Claude" })).toBeVisible();
    expect(editor).toHaveValue("a = 1\nb");
    expect(calls.puts).toHaveLength(0);
  });

  it("a read that left before your save never puts the old text back", async () => {
    let release = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    let reads = 0;
    const options: Options = {};
    const slow = http.get(`${API}/ide/sessions/s1`, async ({ request }) => {
      reads += 1;
      const body = sessionOut(options.session);
      if (reads === 2)
        await Promise.race([gate, new Promise((r) => request.signal.addEventListener("abort", r))]);
      return HttpResponse.json(body);
    });
    options.override = [slow];
    const { user, calls } = renderSession(options);
    const editor = await findEditor();
    await refresh(); // une relecture part avec l'ancien texte...
    await waitFor(() => expect(reads).toBe(2));
    await user.type(editor, "x");
    await waitFor(() => expect(calls.puts).toHaveLength(1), { timeout: AUTOSAVE_MS + 3000 });
    release(); // ...et n'arrive qu'après l'enregistrement
    await settle(300);
    expect(editor).toHaveValue("print('bonjour')\nx");
    expect(screen.queryByText("Claude a modifié ce fichier.")).toBeNull();
  });
});
