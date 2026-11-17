import { useEffect, useRef, type KeyboardEvent } from "react";

/**
 * Faux de `@monaco-editor/react` pour Vitest (alias dans `vitest.config.ts`) : jsdom ne sait pas
 * faire tourner Monaco (ni workers, ni mesures). Une zone de texte rend le champ ; les gestes que
 * l'éditeur réel rend (curseur, Ctrl+Entrée, décorations de la marge) se pilotent par `fakeEditor`.
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

/** L'état du dernier éditeur monté, et les gestes pour le piloter depuis un test. */
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
  /** Déplace le curseur sur `lineNumber`, comme le ferait un clic dans l'éditeur. */
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
/** Le chargeur réel est coupé : `monacoSetup` ne fait que l'appeler avec le paquet local. */
export const loader = { config: () => undefined, init: () => Promise.resolve(fakeMonaco) };
