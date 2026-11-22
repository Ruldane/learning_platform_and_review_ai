import Editor, { type OnMount } from "@monaco-editor/react";
import { useCallback, useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { AnnotationView } from "../viewTypes";
import "./codeEditor.css";
import "./monacoSetup";

interface CodeEditorProps {
  /** Le fichier ouvert : chaque chemin a son propre modèle (et son annulation). */
  path: string;
  value: string;
  readOnly?: boolean;
  annotations: AnnotationView[];
  onChange: (value: string) => void;
  /** La ligne du curseur, à chaque déplacement. Ne réveille jamais le professeur. */
  onCursorLine: (line: number) => void;
  /** Ctrl+Entrée. */
  onRun: () => void;
}

type Paint = (items: AnnotationView[]) => void;

/** Thème clair ; le lecteur d'écran est pris en charge d'office (`accessibilitySupport`). */
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
 * L'éditeur Monaco, **le seul endroit** de l'application qui l'importe. Il rend le texte, la ligne
 * du curseur et Ctrl+Entrée ; il ne connaît ni le professeur ni l'API. Les annotations sont des
 * décorations de la marge (losange plein, texte au survol).
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
