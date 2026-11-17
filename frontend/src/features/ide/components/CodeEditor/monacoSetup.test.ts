import { describe, expect, it } from "vitest";
import setupSource from "./monacoSetup.ts?raw";
import editorSource from "./CodeEditor.tsx?raw";

describe("monaco loading", () => {
  it("monaco is never loaded from a CDN", () => {
    // Le paquet npm est branché sur le chargeur : `@monaco-editor/react` n'ira plus chercher
    // Monaco sur jsdelivr (son réglage par défaut).
    expect(setupSource).toContain("loader.config({ monaco })");
    expect(setupSource).toContain('from "monaco-editor/editor"');
    expect(setupSource).toContain("editor.worker?worker");
    for (const source of [setupSource, editorSource]) {
      expect(source).not.toMatch(/https?:\/\//);
      expect(source).not.toMatch(/jsdelivr|unpkg|cdnjs|cdn\./i);
      expect(source).not.toMatch(/paths\s*:/);
    }
  });

  it("only the editor component imports monaco", async () => {
    const files = import.meta.glob("../../**/*.{ts,tsx}", { query: "?raw", import: "default" });
    const offenders: string[] = [];
    for (const [path, load] of Object.entries(files)) {
      if (/\/(CodeEditor|monacoSetup)\.tsx?$/.test(path) || path.includes(".test.")) continue;
      const text = (await load()) as string;
      if (/@monaco-editor\/react|from "monaco-editor/.test(text)) offenders.push(path);
    }
    expect(offenders).toEqual([]);
  });
});
