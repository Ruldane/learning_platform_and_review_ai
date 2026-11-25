import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { LEVEL_COLORS } from "../levels";
import { useReducedMotion } from "../useReducedMotion";
import type { DomainScoreView } from "../viewTypes";

const TICKS = [0, 25, 50, 75, 100];

interface SkillRadarProps {
  domains: DomainScoreView[];
  /** The action of the empty state (rule 15.4: never a dead end). */
  emptyAction?: { label: string; onClick: () => void };
}

/**
 * Radar of scores per domain, from 0 to 100. The same scores are listed under the drawing:
 * the drawing alone cannot be read by a screen reader.
 */
export function SkillRadar({ domains, emptyAction }: SkillRadarProps) {
  const reduced = useReducedMotion();
  if (domains.length === 0) {
    return (
      <EmptyState
        title={t("skills.radar.empty")}
        description={t("skills.radar.emptyHint")}
        action={emptyAction}
      />
    );
  }
  return (
    <section aria-label={t("skills.radar.label")} className="flex flex-col gap-3">
      <div role="img" aria-label={t("skills.radar.label")} className="h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={domains} outerRadius="75%">
            <PolarGrid />
            <PolarAngleAxis dataKey="domain" tick={{ fill: "var(--foreground)", fontSize: 13 }} />
            {/* Ticks between the first and second ring: they overlap no name. */}
            <PolarRadiusAxis
              domain={[0, 100]}
              ticks={TICKS}
              angle={90 - 180 / domains.length}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <Radar
              name={t("skills.radar.series")}
              dataKey="score"
              stroke={LEVEL_COLORS.validated}
              fill={LEVEL_COLORS.validated}
              fillOpacity={0.3}
              isAnimationActive={!reduced}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <ul aria-label={t("skills.radar.table")} className="grid gap-1 text-sm sm:grid-cols-2">
        {domains.map(({ domain, score }) => (
          <li key={domain}>{t("skills.radar.score", { domain, score })}</li>
        ))}
      </ul>
    </section>
  );
}
