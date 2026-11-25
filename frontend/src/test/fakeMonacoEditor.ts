/**
 * Fake of the `monaco-editor` package for Vitest (alias in `vitest.config.ts`): `monacoSetup`
 * imports its API, functions and worker, which jsdom cannot load. Tests never
 * use them; a dedicated test reads the text of `monacoSetup` to check the local loading.
 */
export default class FakeWorker {}
export const editor = {};
export const languages = {};
