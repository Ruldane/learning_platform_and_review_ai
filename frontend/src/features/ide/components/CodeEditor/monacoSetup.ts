import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/editor";
import "monaco-editor/features/register.all";
import "monaco-editor/languages/definitions/python/register";
import EditorWorker from "monaco-editor/editor/editor.worker?worker";

// Monaco comes from the npm package, never a CDN: `loader.config({ monaco })` stops the
// loading from a remote address of `@monaco-editor/react`. Python has no language service in a
// worker: the only useful worker is the editor's, served by Vite from the same site.
self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });
