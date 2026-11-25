const dayFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" });

export function formatDay(value: string) {
  return dayFormat.format(new Date(`${value}T12:00:00`));
}

export function nextMonday() {
  const now = new Date();
  const days = (8 - now.getDay()) % 7 || 7;
  now.setDate(now.getDate() + days);
  return [
    now.getFullYear(),
    (now.getMonth() + 1).toString().padStart(2, "0"),
    now.getDate().toString().padStart(2, "0"),
  ].join("-");
}
