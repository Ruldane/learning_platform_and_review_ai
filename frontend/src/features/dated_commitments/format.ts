const locale = "en-GB";
const dates = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
const measurements = new Intl.NumberFormat(locale, { maximumFractionDigits: 4 });

export const statuses = {
  scheduled: "datedCommitments.scheduled",
  due: "datedCommitments.due",
  reviewed: "datedCommitments.reviewed",
} as const;

export function normalizeMeasure(value: string) {
  return value.trim().replace(",", ".");
}

export const commitmentsPath = "/etudier/engagements";

export function commitmentPath(id: string) {
  return `${commitmentsPath}/${encodeURIComponent(id)}`;
}

export function formatDue(day: string) {
  return dates.format(new Date(`${day}T12:00:00`));
}

export function formatMeasure(value: string | number) {
  return measurements.format(Number(value));
}
