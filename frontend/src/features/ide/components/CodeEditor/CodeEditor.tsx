import Editor, { type OnMount } from "@monaco-editor/react";
import { useCallback, useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { AnnotationView } from "../viewTypes";
import "./codeEditor.css";
import "./monacoSetup";

interface CodeEditorProps {
  /** The open file: each path has its own model (and its own undo history). */
  path: string;
  value: string;
  readOnly?: boolean;
  annotations: AnnotationView[];
  onChange: (value: string) => void;
  /** The cursor line, on each move. Never wakes the teacher. */
  onCursorLine: (line: number) => void;
  /** Ctrl+Enter. */
  onRun: () => void;
}

type Paint = (items: AnnotationView[]) => void;

/** Light theme; the screen reader is supported by default (`accessibilitySupport`). */
const OPTIONS = {
  accessibilitySupport: "on",
  ariaLabel: t("ide.editor.label"),
  minimap: { enabled: false },
  glyphMargin: true,
  automaticLayout: true,
  scrollBeyondLastLine: false,
  tabSize: 4,
  insertSpaces: true,
  fontSize: 14,
  wordWrap: "on",
} as const;

/**
 * The Monaco editor, **the only place** in the app that imports it. It renders the text, the line
 * of the cursor and Ctrl+Enter; it knows neither the teacher nor the API. Annotations are
 * margin decorations (solid diamond, text on hover).
 */
export function CodeEditor(props: CodeEditorProps) {
  const { path, value, annotations, onChange } = props;
  const latest = useRef(props);
  const paint = useRef<Paint | null>(null);
  useEffect(() => {
    latest.current = props;
  });
  useEffect(() => {
    paint.current?.(annotations);
  }, [annotations]);
  const mount: OnMount = useCallback((editor, monaco) => {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => latest.current.onRun());
    editor.onDidChangeCursorPosition((event) =>
      latest.current.onCursorLine(event.position.lineNumber),
    );
    const collection = editor.createDecorationsCollection([]);
    paint.current = (items) =>
      collection.set(
        items.map((item) => ({
          range: new monaco.Range(item.line, 1, item.line, 1),
          options: {
            isWholeLine: true,
            className: "ide-annotation-line",
            glyphMarginClassName: "ide-annotation-glyph",
            glyphMarginHoverMessage: { value: item.text },
          },
        })),
      );
    paint.current(latest.current.annotations);
  }, []);
  return (
    <div className="h-[26rem] overflow-hidden rounded-xl border border-border">
      <Editor
        path={`inmemory://tremplin/${path}`}
        language="python"
        theme="vs"
        value={value}
        options={{ ...OPTIONS, readOnly: props.readOnly }}
        loading={<p className="p-3 text-sm">{t("ide.editor.loading")}</p>}
        onChange={(text) => onChange(text ?? "")}
        onMount={mount}
      />
    </div>
  );
}
