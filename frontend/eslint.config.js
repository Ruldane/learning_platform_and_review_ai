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
 * - feature     -> sa propre feature + shared ;
 * - feature-components (présentationnels) -> ses propres components + shared/ui, shared/i18n,
 *   shared/lib (ni api.ts, ni hooks/, ni store, ni shared/api) ;
 * - app         -> tout.
 * `test-support` (src/test) n'est importé que par des fichiers de test ou d'infrastructure.
 */
const boundaryPolicies = [
  {
    from: { element: { type: "app" } },
    allow: {
      to: { element: { type: ["app", "feature", "feature-components", "shared", "test-support"] } },
    },
  },
  { from: { element: { type: "shared" } }, allow: { to: { element: { type: "shared" } } } },
  {
    from: { element: { type: "feature" } },
    allow: [
      { to: { element: { type: "shared" } } },
      { to: { element: { types: ["feature", "feature-components"], captured: SAME_FEATURE } } },
    ],
  },
  {
    from: { element: { type: "feature-components" } },
    allow: [
      { to: { element: { type: "shared", captured: { area: ["ui", "i18n", "lib"] } } } },
      { to: { element: { type: "feature-components", captured: SAME_FEATURE } } },
    ],
  },
  // Les tests peuvent importer l'outillage de test.
  {
    from: { file: { categories: "test" } },
    allow: { to: { element: { type: "test-support" } } },
  },
];

export default tseslint.config(
  {
    ignores: ["dist", "node_modules", "coverage", "src/shared/api/schema.d.ts"],
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
    files: ["src/**/*.{ts,tsx}"],
    plugins: { boundaries },
    settings: {
      "boundaries/elements": [
        { type: "app", pattern: "src/app" },
        { type: "test-support", pattern: "src/test" },
        { type: "feature-components", pattern: "src/features/*/components", capture: ["feature"] },
        { type: "feature", pattern: "src/features/*", capture: ["feature"] },
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
