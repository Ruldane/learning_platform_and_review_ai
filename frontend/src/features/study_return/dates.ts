const dayFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" });

export function formatDate(value: string) {
  return dayFormat.format(new Date(value.includes("T") ? value : `${value}T12:00:00`));
}

export function trainingUrl(id: string) {
  return `/etudier/training/${encodeURIComponent(id)}`;
}
