import type { components } from "@/shared/api/schema";
import { t } from "@/shared/i18n/t";
import type { ComparisonView, OfferFactsView } from "./components/viewTypes";

type Result = components["schemas"]["OfferComparisonResult"];
const numbers = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
const display = (value: number | null) => value === null ? t("offerComparison.notScored") : numbers.format(value);
const criterion = (key: Result["scored_criteria"][number]) => t(`offerComparison.criterion.${key}`);

function offerView(
  position: "first" | "second", offer: Result["first"], score: Result["first_score"],
): OfferFactsView {
  return {
    heading: `${t(`offerComparison.${position}`)} · ${offer.title ?? t("offerComparison.unknownTitle")}`,
    company: offer.company,
    score: display(score),
    facts: [
      { label: criterion("match"), value: display(offer.scores.match) },
      { label: criterion("work_mode"), value: offer.remote ?? t("offerComparison.notScored") },
      { label: criterion("location"), value: offer.location ?? t("offerComparison.notScored") },
    ],
    missing: offer.missing.length
      ? `${t("offerComparison.missing")} · ${offer.missing.map(criterion).join(", ")}`
      : t("offerComparison.noMissing"),
    source: `/career/postings/${offer.id}`,
  };
}

export function toComparisonView(result: Result): ComparisonView {
  return {
    rank: t(`offerComparison.rank.${result.leader ?? "none"}`),
    criteria: result.scored_criteria.map((key) =>
      `${criterion(key)} (${result.preferences.weights?.[key] ?? 50})`).join(", "),
    first: offerView("first", result.first, result.first_score),
    second: offerView("second", result.second, result.second_score),
    sensitivity: result.sensitivity.map((row) => ({
      criterion: criterion(row.criterion),
      lower: `${row.lower_weight} · ${display(row.lower_margin)}`,
      higher: `${row.higher_weight} · ${display(row.higher_margin)}`,
    })),
  };
}
