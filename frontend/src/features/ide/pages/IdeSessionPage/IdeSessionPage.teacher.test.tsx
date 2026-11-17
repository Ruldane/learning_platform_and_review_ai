import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { fakeEditor } from "@/test/fakeMonacoReact";
import { noteOut, progress } from "@/test/ideApi";
import { findEditor, renderSession, settle } from "../../ideTestkit";

const waitForUsage = () => screen.findByText(/Séance : 12\s340/);

describe("IdeSessionPage, asking the teacher", () => {
  it("the Indice button sends one hint call with the file, the line and the last run", async () => {
    const { user, calls } = renderSession({ reads: [progress({ exit_code: 1 })] });
    await findEditor();
    await waitForUsage();
    act(() => fakeEditor.moveCursor(4));
    await user.click(screen.getByRole("button", { name: "Indice" }));
    await waitFor(() => expect(calls.teach).toHaveLength(1));
    expect(calls.teach[0]).toEqual({
      trigger: "hint",
      run_id: null,
      file_path: "main.py",
      line: 4,
    });
  });

  it("explains an error only after a failed run, with the run attached", async () => {
    const { user, calls } = renderSession({
      reads: [progress({ exit_code: 1, output: "Boom\n" })],
      preferences: { teacher_mode: "on_demand" },
      usage: { mode_on_demand: true },
    });
    await findEditor();
    const why = screen.getByRole("button", { name: "Pourquoi cette erreur ?" });
    expect(why).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /^Exécuter/ }));
    await screen.findByText(/Terminé \(code 1/);
    await waitFor(() => expect(why).toBeEnabled());
    await user.click(why);
    await waitFor(() => expect(calls.teach).toHaveLength(1));
    expect(calls.teach[0]).toMatchObject({
      trigger: "question",
      question: "Pourquoi cette erreur ?",
      run_id: "r1",
    });
  });

  it("sends a typed question, never an empty one", async () => {
    const { user, calls } = renderSession();
    await findEditor();
    const field = screen.getByRole("textbox", { name: "Ta question" });
    expect(screen.getByRole("button", { name: "Poser la question" })).toBeDisabled();
    await user.type(field, "C'est quoi une liste ?");
    await user.click(screen.getByRole("button", { name: "Poser la question" }));
    await waitFor(() => expect(calls.teach).toHaveLength(1));
    expect(calls.teach[0]).toMatchObject({
      trigger: "question",
      question: "C'est quoi une liste ?",
    });
  });

  it("typing in the editor never calls the teacher", async () => {
    const { user, calls } = renderSession();
    const editor = await findEditor();
    await waitForUsage();
    await user.type(editor, "def add(a, b):");
    act(() => fakeEditor.moveCursor(2));
    await settle(300);
    expect(calls.teach).toHaveLength(0);
  });

  it("says why nothing was started, and when it is the same error as before", async () => {
    const { user } = renderSession({ teach: { skipped: "cap_reached" } });
    await findEditor();
    await user.click(screen.getByRole("button", { name: "Indice" }));
    expect(await screen.findByText(/Le plafond de jetons est atteint/)).toBeInTheDocument();
  });

  it("points to the previous note for the same error at the same place", async () => {
    const { user } = renderSession({ teach: { reference_note_id: "n0" } });
    await findEditor();
    await user.click(screen.getByRole("button", { name: "Indice" }));
    expect(await screen.findByText(/Même erreur au même endroit/)).toBeInTheDocument();
  });

  it("follows the teacher session and reloads the notes when it ends", async () => {
    const { user, sockets, calls } = renderSession({ teach: { session_id: "t1" } });
    await findEditor();
    await user.click(screen.getByRole("button", { name: "Indice" }));
    expect(await screen.findByText("Le professeur réfléchit…")).toBeInTheDocument();
    await waitFor(() => expect(sockets.sockets.length).toBeGreaterThan(0));
    const stream = sockets.sockets.find((s) => s.url.includes("/sessions/t1/stream"));
    expect(stream).toBeDefined();
    act(() => {
      stream?.open().push(councilEvents("t1").completed());
    });
    await waitFor(() => expect(screen.queryByText("Le professeur réfléchit…")).toBeNull());
    expect(calls.teach).toHaveLength(1);
  });

  it("idle timer is off by default: moving to a line starts nothing", async () => {
    const { calls } = renderSession();
    await findEditor();
    await waitForUsage();
    act(() => fakeEditor.moveCursor(2));
    await settle(300);
    expect(calls.teach).toHaveLength(0);
  });

  it("lists the notes by kind, with hint levels, and draws annotations in the margin", async () => {
    renderSession({
      notes: [
        noteOut({ id: "n1", content: "Regarde le signe." }),
        noteOut({ id: "n2", content: "Le signe est faux.", created_at: "2026-11-17T10:06:00Z" }),
        noteOut({
          id: "n3",
          kind: "annotation",
          file_path: "main.py",
          line_start: 1,
          content: "Ici.",
        }),
      ],
    });
    await findEditor();
    const hints = await screen.findByRole("region", { name: "Indices" });
    expect(within(hints).getByText(/Indice 1/)).toBeInTheDocument();
    expect(within(hints).getByText(/Indice 2/)).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Dans la marge" })).getByText("Ici."),
    ).toBeVisible();
    await waitFor(() => expect(fakeEditor.decorations).toHaveLength(1));
    expect(fakeEditor.decorations[0]?.range.startLineNumber).toBe(1);
  });
});
