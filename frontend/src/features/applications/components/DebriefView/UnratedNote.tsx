import { t } from "@/shared/i18n/t";
import { joinNumbers } from "./joinNumbers";

/** Les réponses que le modèle n'a pas pu noter (numéros des questions, à partir de 1) ; rien s'il n'y en a pas. */
export function UnratedNote({ unrated }: { unrated: number[] }) {
  if (unrated.length === 0) return null;
  const numbers = joinNumbers(unrated.map((index) => index + 1));
  const key = unrated.length === 1 ? "one" : "many";
  return (
    <p role="note" className="text-sm text-muted-foreground">
      {t(`applications.debrief.unrated.${key}`, { numbers })}
    </p>
  );
}
