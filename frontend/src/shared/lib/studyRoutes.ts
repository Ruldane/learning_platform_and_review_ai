export function studySessionPath(id: string, kind?: unknown): string {
  const segment = kind === "training" ? "training" : "session";
  return `/etudier/${segment}/${encodeURIComponent(id)}`;
}
