import { describe, expect, it } from "vitest";
import { GRAPH_SCREENS } from "@/features/costs/components/graphs";
import { buildNav } from "./buildNav";
import { FEATURES } from "./registry";

describe("registre des features", () => {
  it("met la connexion en premier : sa porte est la plus extérieure", () => {
    expect(FEATURES[0]?.id).toBe("auth");
    expect(FEATURES[0]?.shell?.gate).toBeDefined();
  });

  it("a des identifiants uniques", () => {
    const ids = FEATURES.map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("expose l'accueil, Apprendre, Étudier, Compétences, Carrière, Candidatures, la mémoire et les réglages dans la navigation", () => {
    const groups = buildNav(FEATURES);
    expect(groups.map((g) => g.section)).toEqual([
      "home",
      "learn",
      "study",
      "skills",
      "career",
      "applications",
      "memory",
      "settings",
    ]);
    expect(groups[0]?.items).toEqual([{ labelKey: "nav.home", path: "/" }]);
    expect(groups[1]?.items.map((item) => item.path)).toEqual([
      "/learn/goals",
      "/learn/council",
      "/learn/programs",
      "/learn/lessons",
      "/learn/lesson-variants",
      "/learn/library",
      "/learn/book",
      "/learn/papers",
    ]);
    expect(groups[2]?.items.map((item) => item.path)).toEqual([
      "/study/session",
      "/study/training",
      "/study/debates",
      "/study/return",
      "/study/reviews",
      "/study/quiz",
      "/mobile",
      "/study/error-atlas",
      "/study/shared-planning",
      "/study/commitments",
      "/study/journal",
      "/code",
      "/on-call",
      "/learn/decisions",
      "/study/contradictory-watch",
      "/study/incident-replay",
      "/study/investigations",
      "/study/meeting-modules",
      "/study/podcast",
    ]);
    expect(groups[3]?.items).toEqual([
      { labelKey: "skills.nav.map", path: "/skills" },
      { labelKey: "galaxy.nav", path: "/skills/galaxy" },
      { labelKey: "projects.nav.portfolio", path: "/skills/portfolio" },
      { labelKey: "contributions.title", path: "/skills/contributions" },
      { labelKey: "skillTransfer.nav", path: "/skills/transfer" },
      { labelKey: "gradeAppeals.title", path: "/skills/appeals" },
    ]);
    expect(groups[4]?.items).toEqual([
      { labelKey: "cv.nav.profile", path: "/career/profile" },
      { labelKey: "cv.nav.cv", path: "/career/cv" },
      { labelKey: "gap.nav.postings", path: "/career/postings" },
      { labelKey: "gap.nav.overview", path: "/career/gaps" },
      { labelKey: "radar.nav.radar", path: "/career/radar" },
      { labelKey: "portfolio.title", path: "/career/portfolio-site" },
      { labelKey: "missions.title", path: "/career/missions" },
      { labelKey: "proofPackets.title", path: "/career/evidence" },
      { labelKey: "mentorReviews.title", path: "/career/mentor-review" },
      { labelKey: "futureSelf.title", path: "/career/future-self" },
      { labelKey: "projectHandoffs.title", path: "/career/project-handoffs" },
      { labelKey: "skillMarket.title", path: "/career/skills" },
      { labelKey: "linkedInDrafts.title", path: "/career/linkedin" },
      { labelKey: "blindAssessment.title", path: "/career/blind-assessment" },
      { labelKey: "recruitmentProcess.title", path: "/career/recruitment-process" },
      { labelKey: "offerComparison.title", path: "/career/offer-comparison" },
    ]);
    expect(groups[5]?.items.map((item) => item.path)).toEqual([
      "/applications",
      "/applications/reminders",
      "/applications/interview",
    ]);
    expect(groups[6]?.items.map((item) => item.path)).toEqual([
      "/memory",
      "/memory/map",
      "/memory/search-bench",
      "/memory/documents",
      "/memory/brain",
      "/memory/reading",
    ]);
    expect(groups[7]?.items).toEqual([
      { labelKey: "settings.models.navLabel", path: "/settings/models" },
      { labelKey: "settings.search.navLabel", path: "/settings/search" },
      { labelKey: "research.nav.bench", path: "/settings/search/probe" },
      { labelKey: "settings.availability.navLabel", path: "/settings/availability" },
      { labelKey: "settings.study.navLabel", path: "/settings/study" },
      { labelKey: "settings.style.navLabel", path: "/settings/style" },
      { labelKey: "calendar.title", path: "/settings/calendar" },
      { labelKey: "costs.nav.costs", path: "/settings/costs" },
      { labelKey: "routines.title", path: "/settings/routines" },
      { labelKey: "costs.nav.log", path: "/settings/agent-log" },
      { labelKey: "account.nav.data", path: "/settings/data" },
      { labelKey: "mcp.nav.access", path: "/settings/mcp" },
      { labelKey: "messageReview.title", path: "/settings/message-review" },
      { labelKey: "surpriseInterview.title", path: "/settings/surprise-interviews" },
    ]);
  });

  it("le journal des agents ne mène qu'à des écrans qui existent", () => {
    const known = new Set([
      ...FEATURES.flatMap((f) => f.nav?.map((entry) => entry.path) ?? []),
      ...FEATURES.flatMap((f) =>
        f.routes.map((route) => `/${(route.path ?? "").replace(/^\//, "")}`),
      ),
    ]);
    for (const path of Object.values(GRAPH_SCREENS)) expect(known).toContain(path);
  });
});
