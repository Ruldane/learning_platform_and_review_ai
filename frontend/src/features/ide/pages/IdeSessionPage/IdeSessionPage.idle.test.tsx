import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fakeEditor } from "@/test/fakeMonacoReact";
import { IDLE_MS } from "../../hooks/useIdleTeach";
import { findEditor, renderSession } from "../../ideTestkit";

describe("IdeSessionPage, 30 s idle option", () => {
  afterEach(() => vi.useRealTimers());

  async function ready(options: Parameters<typeof renderSession>[0]) {
    const view = renderSession(options);
    await findEditor();
    await screen.findByText(/Séance : 12\s340/);
    await screen.findByRole("checkbox", { name: /30 s sans bouger de ligne/ });
    return view;
  }

  it("idle timer fires once after 30 s when enabled", async () => {
    const { calls } = await ready({ preferences: { idle_trigger: true } });
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    act(() => fakeEditor.moveCursor(2));
    await act(() => vi.advanceTimersByTimeAsync(IDLE_MS - 1));
    expect(calls.teach).toHaveLength(0);
    await act(() => vi.advanceTimersByTimeAsync(1));
    vi.useRealTimers();
    await waitFor(() => expect(calls.teach).toHaveLength(1));
    expect(calls.teach[0]).toEqual({ trigger: "idle", file_path: "main.py", line: 2 });
  });

  it("is off by default: the same wait starts nothing", async () => {
    const { calls } = await ready({});
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    act(() => fakeEditor.moveCursor(2));
    await act(() => vi.advanceTimersByTimeAsync(IDLE_MS * 2));
    vi.useRealTimers();
    expect(calls.teach).toHaveLength(0);
  });
});
