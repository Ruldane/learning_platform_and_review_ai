import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/editor";
import "monaco-editor/features/register.all";
import "monaco-editor/languages/definitions/python/register";
import EditorWorker from "monaco-editor/editor/editor.worker?worker";

// Monaco vient du paquet npm, jamais d'un CDN : `loader.config({ monaco })` coupe le chargement
// par adresse distante de `@monaco-editor/react`. Python n'a pas de service de langage dans un
// worker : le seul worker utile est celui de l'éditeur, servi par Vite depuis le même site.
self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });
