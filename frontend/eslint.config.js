import js from "@eslint/js";
import boundaries from "eslint-plugin-boundaries";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const SAME_FEATURE = { feature: "{{ from.captured.feature }}" };

/**
 * Règles de découpage (voir SPEC et DECISIONS D32) :
 * - shared      -> shared seulement ;
 * - session-ui  (shared/session-ui, composants de session présentationnels) -> lui-même +
 *   shared/ui, i18n, lib et realtime (types et registre de rendu seulement, voir le bloc
 *   `no-restricted-imports` plus bas) ; jamais shared/api, features ni app ;
 * - feature     -> sa propre feature + shared + session-ui ;
 * - feature-components (présentationnels) -> ses propres components + shared/ui, shared/i18n,
 *   shared/lib + session-ui (ni api.ts, ni hooks/, ni store, ni shared/api) ;
 * - app         -> tout.
 * `test-support` (src/test) n'est importé que par des fichiers de test ou d'infrastructure ; il
 * peut importer `shared` (jamais `features` ni `app`).
 */
const boundaryPolicies = [
  {
    from: { element: { type: "app" } },
    allow: {
      to: {
        element: {
          type: ["app", "feature", "feature-components", "shared", "session-ui", "test-support"],
        },
      },
    },
  },
  { from: { element: { type: "shared" } }, allow: { to: { element: { type: "shared" } } } },
  {
    from: { element: { type: "session-ui" } },
    allow: [
      { to: { element: { type: "session-ui" } } },
      {
        to: { element: { type: "shared", captured: { area: ["ui", "i18n", "lib", "realtime"] } } },
      },
    ],
  },
  {
    from: { element: { type: "feature" } },
    allow: [
      { to: { element: { types: ["shared", "session-ui"] } } },
      { to: { element: { types: ["feature", "feature-components"], captured: SAME_FEATURE } } },
    ],
  },
  {
    from: { element: { type: "feature-components" } },
    allow: [
      { to: { element: { type: "shared", captured: { area: ["ui", "i18n", "lib"] } } } },
      { to: { element: { type: "session-ui" } } },
      { to: { element: { type: "feature-components", captured: SAME_FEATURE } } },
    ],
  },
  // L'outillage de test (faux socket, etc.) s'appuie sur les types et modules partagés.
  { from: { element: { type: "test-support" } }, allow: { to: { element: { type: "shared" } } } },
  // Les tests peuvent importer l'outillage de test.
  {
    from: { file: { categories: "test" } },
    allow: { to: { element: { type: "test-support" } } },
  },
];

export default tseslint.config(
  {
    ignores: [
      "dist",
      "node_modules",
      "coverage",
      "playwright-report",
      "test-results",
      "src/shared/api/schema.d.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  react.configs.flat.recommended,
  react.configs.flat["jsx-runtime"],
  reactHooks.configs.flat.recommended,
  {
    files: ["**/*.{ts,tsx,js,mjs}"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    settings: {
      react: { version: "detect" },
      "import/resolver": {
        typescript: { alwaysTryTypes: true, project: "./tsconfig.app.json" },
      },
    },
    rules: {
      "max-lines": ["error", { max: 300 }],
      "max-lines-per-function": ["error", { max: 50, skipBlankLines: true, skipComments: true }],
      "react/no-multi-comp": "error",
      "react/prop-types": "off",
    },
  },
  {
    // Les blocs `describe` regroupent tous les cas d'un fichier : ils dépassent 50 lignes.
    files: ["**/*.test.{ts,tsx}"],
    rules: { "max-lines-per-function": "off" },
  },
  {
    // Parcours de bout en bout (Playwright) : hors de `src`, donc hors des règles de feature ; un
    // parcours se lit d'un bout à l'autre et ses étapes dépassent 50 lignes.
    files: ["e2e/**/*.ts", "playwright.config.ts"],
    rules: { "max-lines-per-function": "off" },
  },
  {
    // Les composants de session sont présentationnels : pas d'API, de store ni de hook de données
    // (seuls `realtime/types` et le registre `realtime/eventRenderers` sont importables).
    files: ["src/shared/session-ui/**/*.{ts,tsx}"],
    ignores: ["**/*.test.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/realtime/*", "!**/realtime/types", "!**/realtime/eventRenderers"],
              message: "session-ui reste présentationnel : ni store, ni flux, ni hook de données.",
            },
            {
              group: ["**/shared/api/*", "**/shared/api"],
              message: "Pas d'appel API dans session-ui.",
            },
            {
              group: ["@tanstack/*", "zustand", "zustand/*"],
              message: "Pas de données dans session-ui.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { boundaries },
    settings: {
      "boundaries/elements": [
        { type: "app", pattern: "src/app" },
        { type: "test-support", pattern: "src/test" },
        { type: "feature-components", pattern: "src/features/*/components", capture: ["feature"] },
        { type: "feature", pattern: "src/features/*", capture: ["feature"] },
        // Avant `shared` : le premier élément qui correspond l'emporte.
        { type: "session-ui", pattern: "src/shared/session-ui" },
        { type: "shared", pattern: "src/shared/*", capture: ["area"] },
      ],
      // Point d'entrée : monte `app`, hors périmètre des règles.
      "boundaries/ignore": ["src/main.tsx"],
      "boundaries/files": [{ pattern: "**/*.test.{ts,tsx}", category: "test" }],
    },
    rules: {
      "boundaries/dependencies": [
        "error",
        { default: "disallow", checkAllOrigins: false, policies: boundaryPolicies },
      ],
    },
  },
);
