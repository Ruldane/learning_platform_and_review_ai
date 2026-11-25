import { t } from "@/shared/i18n/t";
import { joinNumbers } from "./joinNumbers";

/** The answers the model could not score (question numbers, from 1); nothing if there are none. */
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
