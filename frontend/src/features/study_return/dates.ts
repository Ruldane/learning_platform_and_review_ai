const frenchDay = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });

export function formatDate(value: string) {
  return frenchDay.format(new Date(value.includes("T") ? value : `${value}T12:00:00`));
}

export function trainingUrl(id: string) {
  return `/etudier/training/${encodeURIComponent(id)}`;
}
