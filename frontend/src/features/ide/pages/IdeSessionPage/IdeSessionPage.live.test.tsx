import { focusManager } from "@tanstack/react-query";
import { act, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { errorBody } from "@/test/authApi";
import { API } from "@/test/councilApi";
import { noteOut, progress, runOut, sessionOut } from "@/test/ideApi";
import { LIVE_MS } from "../../hooks/live";
import { findEditor, refresh, renderSession, settle } from "../../ideTestkit";

const outputRegion = () => screen.getByRole("region", { name: "Output" });

afterEach(() => {
  vi.useRealTimers();
  focusManager.setFocused(undefined);
});

describe("IdeSessionPage, live refresh", () => {
  it("re-reads the session, the notes and the runs every 3 s while the tab is visible", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { calls } = renderSession();
    await findEditor();
    await waitFor(() => expect(calls.noteReads).toBe(1));
    expect([calls.sessionReads, calls.runListReads]).toEqual([1, 1]);
    await act(() => vi.advanceTimersByTimeAsync(LIVE_MS));
    await waitFor(() => expect(calls.noteReads).toBe(2));
    expect([calls.sessionReads, calls.runListReads]).toEqual([2, 2]);
    await act(() => vi.advanceTimersByTimeAsync(LIVE_MS));
    await waitFor(() => expect(calls.noteReads).toBe(3));
  });

  it("stops when the tab is hidden and reads again when it comes back", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { calls } = renderSession();
    await findEditor();
    await waitFor(() => expect(calls.noteReads).toBe(1));
    act(() => focusManager.setFocused(false));
    await act(() => vi.advanceTimersByTimeAsync(LIVE_MS * 4));
    expect([calls.noteReads, calls.sessionReads, calls.runListReads]).toEqual([1, 1, 1]);
    act(() => focusManager.setFocused(true));
    await waitFor(() => expect(calls.noteReads).toBe(2));
    expect([calls.sessionReads, calls.runListReads]).toEqual([2, 2]);
  });

  it("keeps the session and its edits when a live read fails", async () => {
    let reads = 0;
    const flaky = http.get(`${API}/ide/sessions/s1`, () => {
      reads += 1;
      if (reads === 1) return HttpResponse.json(sessionOut());
      return HttpResponse.json(errorBody("boom", "Panne."), { status: 500 });
    });
    const { user } = renderSession({ override: [flaky] });
    const editor = await findEditor();
    await user.type(editor, "x");
    await refresh();
    await waitFor(() => expect(reads).toBeGreaterThan(1));
    await settle(200);
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
    expect(editor).toHaveValue("print('bonjour')\nx");
  });
});

describe("IdeSessionPage, Claude's runs", () => {
  const claudeRun = (over: Record<string, unknown> = {}) => runOut({ id: "rc1", ...over });

  it("shows a run Claude started, marked, without taking the focus", async () => {
    const options: Parameters<typeof renderSession>[0] = {
      reads: [progress({ id: "rc1", output: "salut de Claude\n", next_offset: 16 })],
    };
    renderSession(options);
    const editor = await findEditor();
    editor.focus();
    expect(screen.getByText("Nothing has run yet. Press Ctrl+Enter.")).toBeInTheDocument();
    options.runs = [claudeRun({ status: "running" })];
    await refresh();
    expect(await screen.findByText("Run by Claude")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("log", { name: "Program output" }).textContent).toBe(
        "salut de Claude\n",
      ),
    );
    expect(outputRegion()).not.toHaveFocus();
    expect(editor).toHaveFocus();
  });

  it("does not wake the teacher when Claude's run fails", async () => {
    const options: Parameters<typeof renderSession>[0] = {
      reads: [progress({ id: "rc1", exit_code: 1, output: "Traceback\n", next_offset: 10 })],
    };
    const { calls } = renderSession(options);
    await findEditor();
    await screen.findByText(/Session: 12,340/);
    options.runs = [claudeRun()];
    await refresh();
    expect(await screen.findByText(/Finished \(code 1/)).toBeInTheDocument();
    await settle(500);
    expect(calls.teach).toHaveLength(0);
  });

  it("does not bring back an old finished run when the page opens", async () => {
    renderSession({ runs: [claudeRun()] });
    await findEditor();
    await settle(300);
    expect(screen.queryByText("Run by Claude")).toBeNull();
    expect(screen.getByText("Nothing has run yet. Press Ctrl+Enter.")).toBeInTheDocument();
  });

  it("follows a run of Claude's that is still running when the page opens", async () => {
    renderSession({
      runs: [claudeRun({ status: "running" })],
      reads: [progress({ id: "rc1", output: "en cours\n", next_offset: 9 })],
    });
    await findEditor();
    expect(await screen.findByText("Run by Claude")).toBeInTheDocument();
  });

  it("an own run stays unmarked and still takes the focus", async () => {
    const { user } = renderSession({ runs: [runOut({ id: "r1", origin: "app" })] });
    await findEditor();
    await user.click(screen.getByRole("button", { name: /^Run code/ }));
    await screen.findByText("Finished (code 0, 120 ms).");
    expect(screen.queryByText("Run by Claude")).toBeNull();
    await waitFor(() => expect(outputRegion()).toHaveFocus());
  });
});

describe("IdeSessionPage, notes from Claude", () => {
  it("names Claude on a note written through the MCP", async () => {
    const options: Parameters<typeof renderSession>[0] = { notes: [] };
    renderSession(options);
    await findEditor();
    options.notes = [
      noteOut({
        id: "n9",
        author: "claude",
        author_label: "Mon jeton",
        origin: "mcp",
        content: "Pense au cas zéro.",
      }),
      noteOut({
        id: "n8",
        kind: "explanation",
        author: "claude",
        author_label: null,
        origin: "mcp",
        content: "Une boucle répète.",
        created_at: "2026-11-17T10:06:00Z",
      }),
    ];
    await refresh();
    const hint = await screen.findByRole("article", { name: /^Claude \(Mon jeton\)/ });
    expect(within(hint).getByText("Pense au cas zéro.")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Claude" })).toBeInTheDocument();
  });
});

describe("IdeSessionPage, Claude's write switch", () => {
  const writes = () =>
    screen.findByRole("switch", { name: "Claude can write to my files" });

  it("is off by default and says so", async () => {
    renderSession();
    expect(await writes()).not.toBeChecked();
    expect(screen.getByText(/: Not allowed$/)).toBeInTheDocument();
  });

  it("is set from the page and keeps the other settings", async () => {
    const { user, calls } = renderSession({ preferences: { session_cap: 5000, day_cap: 9000 } });
    const toggle = await writes();
    await user.click(toggle);
    await waitFor(() => expect(calls.prefs).toHaveLength(1));
    expect(calls.prefs[0]).toEqual({
      teacher_mode: "auto",
      idle_trigger: false,
      teacher_style: "guide",
      mcp_can_write_files: true,
      session_cap: 5000,
      day_cap: 9000,
    });
    await waitFor(() => expect(toggle).toBeChecked());
  });

  it("shows it on when the server says so, and turns it off again", async () => {
    const { user, calls } = renderSession({ preferences: { mcp_can_write_files: true } });
    const toggle = await writes();
    await waitFor(() => expect(toggle).toBeChecked());
    await user.click(toggle);
    await waitFor(() => expect(calls.prefs).toHaveLength(1));
    expect(calls.prefs[0]).toMatchObject({ mcp_can_write_files: false });
  });
});
