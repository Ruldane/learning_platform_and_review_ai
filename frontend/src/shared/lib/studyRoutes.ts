export function studySessionPath(id: string, kind?: unknown): string {
  const segment = kind === "training" ? "training" : "session";
  return `/study/${segment}/${encodeURIComponent(id)}`;
}
