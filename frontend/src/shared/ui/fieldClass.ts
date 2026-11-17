/**
 * Classes communes aux champs de saisie natifs (texte, mot de passe, liste déroulante). Un champ
 * `aria-invalid` change de cadre : l'état n'est jamais porté par la seule couleur d'un texte.
 */
export const fieldClass =
  "h-8 w-full min-w-0 rounded-lg border border-border bg-background px-2.5 text-sm outline-none " +
  "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20";
