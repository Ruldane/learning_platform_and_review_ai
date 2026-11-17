/**
 * Faux du paquet `monaco-editor` pour Vitest (alias dans `vitest.config.ts`) : `monacoSetup` en
 * importe l'API, les fonctions et le worker, que jsdom ne sait pas charger. Les tests ne s'en
 * servent jamais ; un test dédié lit le texte de `monacoSetup` pour y vérifier le chargement local.
 */
export default class FakeWorker {}
export const editor = {};
export const languages = {};
