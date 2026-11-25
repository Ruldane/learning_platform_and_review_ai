import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fakeEditor } from "@/test/fakeMonacoReact";
import { CodeEditor } from "./CodeEditor";

const props = () => ({
  path: "main.py",
  value: "print(1)\n",
  annotations: [],
  onChange: vi.fn(),
  onCursorLine: vi.fn(),
  onRun: vi.fn(),
});

describe("CodeEditor", () => {
  beforeEach(() => fakeEditor.reset());

  it("reports cursor line and never calls the teacher on typing", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const handlers = props();
    render(<CodeEditor {...handlers} />);
    const editor = await screen.findByRole("textbox", { name: "Session Python code" });
    act(() => fakeEditor.moveCursor(3));
    expect(handlers.onCursorLine).toHaveBeenCalledWith(3);
    await userEvent.setup().type(editor, "x");
    expect(handlers.onChange).toHaveBeenCalledWith("print(1)\nx");
    // Le composant ne connaît ni l'API ni le professeur : taper n'envoie rien.
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("runs on Ctrl+Enter, once per press", async () => {
    const handlers = props();
    render(<CodeEditor {...handlers} />);
    const editor = await screen.findByRole("textbox", { name: "Session Python code" });
    await userEvent.setup().type(editor, "{Control>}{Enter}{/Control}");
    expect(handlers.onRun).toHaveBeenCalledTimes(1);
  });

  it("draws annotations in the margin and moves them with the notes", async () => {
    const handlers = props();
    const note = { id: "n1", line: 2, text: "Ce nom est trompeur." };
    const { rerender } = render(<CodeEditor {...handlers} annotations={[note]} />);
    await screen.findByRole("textbox", { name: "Session Python code" });
    expect(fakeEditor.decorations).toHaveLength(1);
    expect(fakeEditor.decorations[0]?.range.startLineNumber).toBe(2);
    expect(fakeEditor.decorations[0]?.options.glyphMarginHoverMessage?.value).toBe(note.text);
    rerender(<CodeEditor {...handlers} annotations={[]} />);
    expect(fakeEditor.decorations).toHaveLength(0);
  });
});
