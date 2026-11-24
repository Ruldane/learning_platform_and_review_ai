import { describe, expect, it } from "vitest";
import { applicationsManifest } from "./manifest";

describe("applicationsManifest", () => {
  it("declares the board with the drawer as its child, the reminders, the new application, the kit, the interviews and the committee", () => {
    expect(applicationsManifest.id).toBe("applications");
    expect(applicationsManifest.routes.map((route) => route.path)).toEqual([
      "candidatures",
      "applications/reminders",
      "applications/new",
      "applications/interview",
      "applications/:applicationId/kit",
      "applications/:applicationId/interview",
      "applications/:applicationId/committee",
    ]);
    expect(applicationsManifest.routes[0]?.children?.map((route) => route.path)).toEqual([
      ":applicationId",
    ]);
  });

  it("asks for the full width for the board", () => {
    expect(applicationsManifest.routes[0]?.handle).toEqual({ wide: true });
  });

  it("puts the board first, the reminders second and the free interview third in the Candidatures section", () => {
    const nav = applicationsManifest.nav ?? [];
    expect(nav.map(({ section, path, order }) => ({ section, path, order }))).toEqual([
      { section: "applications", path: "/applications", order: 1 },
      { section: "applications", path: "/applications/reminders", order: 2 },
      { section: "applications", path: "/applications/interview", order: 3 },
    ]);
  });

  it("gives only the reminders a badge, read aloud as « n relances dues »", () => {
    const [board, reminders, interview] = applicationsManifest.nav ?? [];
    expect(board?.useBadge).toBeUndefined();
    expect(interview?.useBadge).toBeUndefined();
    expect(reminders?.useBadge).toBeTypeOf("function");
    expect(reminders?.badgeLabel?.(3)).toBe("3 relances dues");
    expect(reminders?.badgeLabel?.(1)).toBe("1 relance due");
  });
});
