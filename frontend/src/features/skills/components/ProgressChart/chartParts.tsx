import { CartesianGrid, Legend, Line, Tooltip, XAxis, YAxis } from "recharts";
import { t } from "@/shared/i18n/t";
import { shortDay } from "@/shared/lib/format";
import { LEVEL_COLORS, type LevelKey } from "../levels";

/** Les quatre niveaux d'une compétence présente, du premier au plus haut ; « absent » n'a pas de courbe. */
export const LEVELS: readonly Exclude<LevelKey, "absent">[] = [
  "declare",
  "en_cours",
  "valide",
  "prouve",
];
const COUNTS_AXIS = "counts";
const SCORE_AXIS = "score";

/** Titre d'axe centré sur l'axe (sans `textAnchor`, il part du milieu et sort du cadre). */
const axisLabel = (value: string) => ({ value, style: { textAnchor: "middle" as const } });

/**
 * Les éléments du graphique : grille, deux axes (nombre de compétences à gauche, score de 0 à 100 à
 * droite), infobulle, légende, une courbe par niveau et la courbe du score en pointillés. Une
 * fonction et non un composant : Recharts lit ses éléments tels que le graphique les reçoit.
 */
export function chartParts(animate: boolean) {
  return (
    <>
      <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
      <XAxis dataKey="weekStart" tickFormatter={shortDay} />
      <YAxis
        yAxisId={COUNTS_AXIS}
        allowDecimals={false}
        label={{ ...axisLabel(t("skills.progress.counts")), angle: -90, position: "insideLeft" }}
      />
      <YAxis
        yAxisId={SCORE_AXIS}
        orientation="right"
        domain={[0, 100]}
        label={{ ...axisLabel(t("skills.progress.scoreAxis")), angle: 90, position: "insideRight" }}
      />
      <Tooltip
        labelFormatter={(label) => t("skills.progress.week", { day: shortDay(String(label)) })}
      />
      <Legend itemSorter={null} />
      {LEVELS.map((level) => (
        <Line
          key={level}
          yAxisId={COUNTS_AXIS}
          dataKey={level}
          name={t(`skills.level.${level}`)}
          stroke={LEVEL_COLORS[level]}
          strokeWidth={2}
          dot={{ r: 3 }}
          isAnimationActive={animate}
        />
      ))}
      <Line
        yAxisId={SCORE_AXIS}
        dataKey="score"
        name={t("skills.progress.score")}
        stroke="var(--foreground)"
        strokeWidth={2}
        strokeDasharray="6 4"
        dot={{ r: 3 }}
        isAnimationActive={animate}
      />
    </>
  );
}
