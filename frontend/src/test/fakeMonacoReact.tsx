import { useEffect, useRef, type KeyboardEvent } from "react";

/**
 * Fake of `@monaco-editor/react` for Vitest (alias in `vitest.config.ts`): jsdom cannot
 * run Monaco (no workers, no measurements). A textarea renders the field; the gestures the
 * real editor renders (cursor, Ctrl+Enter, margin decorations) are driven through `fakeEditor`.
 */

const CTRL_CMD = 2048;
const ENTER = 3;

export interface FakeDecoration {
  range: { startLineNumber: number };
  options: { glyphMarginHoverMessage?: { value: string }; glyphMarginClassName?: string };
}

class Range {
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  constructor(startLine: number, startColumn: number, endLine: number, endColumn: number) {
    this.startLineNumber = startLine;
    this.startColumn = startColumn;
    this.endLineNumber = endLine;
    this.endColumn = endColumn;
  }
}

const fakeMonaco = { KeyMod: { CtrlCmd: CTRL_CMD }, KeyCode: { Enter: ENTER }, Range };

/** The state of the last mounted editor, and the gestures to drive it from a test. */
export const fakeEditor = {
  commands: new Map<number, () => void>(),
  cursorListeners: [] as Array<(event: { position: { lineNumber: number } }) => void>,
  decorations: [] as FakeDecoration[],
  mounts: 0,
  reset() {
    this.commands.clear();
    this.cursorListeners = [];
    this.decorations = [];
    this.mounts = 0;
  },
  /** Moves the cursor to `lineNumber`, as a click in the editor would. */
  moveCursor(lineNumber: number) {
    for (const listener of this.cursorListeners) listener({ position: { lineNumber } });
  },
};

function createEditor() {
  return {
    addCommand(keybinding: number, handler: () => void) {
      fakeEditor.commands.set(keybinding, handler);
    },
    onDidChangeCursorPosition(listener: (event: { position: { lineNumber: number } }) => void) {
      fakeEditor.cursorListeners.push(listener);
    },
    createDecorationsCollection(initial: FakeDecoration[]) {
      fakeEditor.decorations = initial;
      return {
        set(next: FakeDecoration[]) {
          fakeEditor.decorations = next;
        },
        clear() {
          fakeEditor.decorations = [];
        },
      };
    },
  };
}

interface FakeEditorProps {
  value?: string;
  path?: string;
  options?: { ariaLabel?: string };
  onChange?: (value: string | undefined) => void;
  onMount?: (editor: ReturnType<typeof createEditor>, monaco: typeof fakeMonaco) => void;
}

export default function Editor({ value, path, options, onChange, onMount }: FakeEditorProps) {
  const mounted = useRef(false);
  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    fakeEditor.mounts += 1;
    onMount?.(createEditor(), fakeMonaco);
  });
  const onKeyDown = (event: KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      fakeEditor.commands.get(CTRL_CMD | ENTER)?.();
    }
  };
  return (
    <textarea
      aria-label={options?.ariaLabel}
      data-path={path}
      value={value}
      onChange={(event) => onChange?.(event.target.value)}
      onKeyDown={onKeyDown}
    />
  );
}

export { Editor };
/** The real loader is cut: `monacoSetup` only calls it with the local package. */
export const loader = { config: () => undefined, init: () => Promise.resolve(fakeMonaco) };
