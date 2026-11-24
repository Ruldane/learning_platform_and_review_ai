import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { progress, usageOut } from "@/test/ideApi";
import { expectCoherentOutline } from "@/test/headingOutline";
import { findEditor, renderSession, settle } from "../../ideTestkit";

const RUN = { name: /^Run code/ };
const usageBadge = async () =>
  within(await screen.findByRole("group", { name: "Professor usage" }))
    .getByText("On request")
    .closest("p") as HTMLElement;
const failure = progress({
  output: "Traceback\nNameError\n",
  next_offset: 20,
  exit_code: 1,
});

describe("IdeSessionPage, running code", () => {
  it("OutputPanel polls by offset and stops at the end", async () => {
    const running = { status: "running", exit_code: null, duration_ms: null };
    const { user, calls } = renderSession({
      reads: [
        progress({ ...running, output: "Bon", next_offset: 3 }),
        progress({ ...running, output: "jour\n", next_offset: 8 }),
        progress({ output: "!\n", next_offset: 10 }),
      ],
    });
    await findEditor();
    await user.click(screen.getByRole("button", RUN));
    expect(await screen.findByText("Finished (code 0, 120 ms).")).toBeInTheDocument();
    // Chaque lecture repart du décalage rendu par la précédente, la sortie est mise bout à bout.
    expect(calls.reads).toEqual([0, 3, 8]);
    expect(screen.getByRole("log", { name: "Program output" }).textContent).toBe(
      "Bonjour\n!\n",
    );
    await settle(800);
    expect(calls.reads).toHaveLength(3);
    expect(calls.runs).toEqual([{ kind: "run" }]);
  });

  it("runs on Ctrl+Enter and puts the focus on the output, not on body", async () => {
    const { user, calls } = renderSession();
    const editor = await findEditor();
    await user.type(editor, "{Control>}{Enter}{/Control}");
    await waitFor(() => expect(calls.runs).toHaveLength(1));
    const output = screen.getByRole("region", { name: "Output" });
    await waitFor(() => expect(output).toHaveFocus());
    expect(document.body).not.toHaveFocus();
    await screen.findByText("Finished (code 0, 120 ms).");
  });

  it("run error triggers exactly one teach call", async () => {
    const { user, calls } = renderSession({ reads: [failure] });
    await findEditor();
    await screen.findByText(/Session: 12,340/);
    await user.click(screen.getByRole("button", RUN));
    await waitFor(() => expect(calls.teach).toHaveLength(1));
    expect(calls.teach[0]).toEqual({
      trigger: "run_error",
      run_id: "r1",
      file_path: "main.py",
      line: null,
    });
    await settle(800);
    expect(calls.teach).toHaveLength(1);
    expect(await screen.findByText("The professor is writing…")).toBeInTheDocument();
  });

  it("a run that succeeds never calls the teacher", async () => {
    const { user, calls } = renderSession({ reads: [progress({ output: "ok\n" })] });
    await findEditor();
    await screen.findByText(/Session: 12,340/);
    await user.click(screen.getByRole("button", RUN));
    await screen.findByText("Finished (code 0, 120 ms).");
    await settle(300);
    expect(calls.teach).toHaveLength(0);
  });

  it('cap reached shows "On request" and no automatic call', async () => {
    const { user, calls } = renderSession({
      reads: [failure],
      usage: usageOut({ session_tokens: 100_000, mode_on_demand: true }),
    });
    await findEditor();
    expect(await usageBadge()).toHaveTextContent("On request");
    await user.click(screen.getByRole("button", RUN));
    await screen.findByText(/Finished \(code 1/);
    await settle(500);
    expect(calls.teach).toHaveLength(0);
    // Appeler le professeur reste possible à la main.
    await user.click(screen.getByRole("button", { name: "Why this error?" }));
    await waitFor(() => expect(calls.teach).toHaveLength(1));
  });

  it("the on-demand choice also keeps the teacher quiet", async () => {
    const { user, calls } = renderSession({
      reads: [failure],
      preferences: { teacher_mode: "on_demand" },
      usage: usageOut({ mode_on_demand: true }),
    });
    await findEditor();
    expect(await usageBadge()).toHaveTextContent("On request");
    await user.click(screen.getByRole("button", RUN));
    await screen.findByText(/Finished \(code 1/);
    await settle(500);
    expect(calls.teach).toHaveLength(0);
  });

  it("saves the code before running it", async () => {
    const { user, calls } = renderSession();
    const editor = await findEditor();
    await user.type(editor, "x");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    await user.click(screen.getByRole("button", RUN));
    await screen.findByText("Finished (code 0, 120 ms).");
    expect(calls.puts).toHaveLength(1);
    expect(calls.puts[0]).toMatchObject({
      files: { "main.py": "print('bonjour')\nx" },
      entry: "main.py",
    });
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("shows the server message when a run is already in progress", async () => {
    const { user } = renderSession({ run: "busy" });
    await findEditor();
    await user.click(screen.getByRole("button", RUN));
    expect(await screen.findByRole("alert")).toHaveTextContent("Une exécution est déjà en cours.");
    expect(screen.getByRole("button", RUN)).toBeEnabled();
  });

  it("keeps a coherent heading outline and a labelled editor", async () => {
    renderSession();
    await findEditor();
    expectCoherentOutline();
    expect(screen.getByRole("heading", { level: 1, name: "Additionner" })).toBeInTheDocument();
    for (const name of ["Output", "Professor", "Editor"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });
});
