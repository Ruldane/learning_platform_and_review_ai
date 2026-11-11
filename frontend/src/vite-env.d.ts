/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Adresse du back (sans /api/v1). Figée dans le bundle à la construction. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
