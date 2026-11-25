import type { FeatureManifest } from "@/shared/lib/feature";
import { ProgramIndexPage } from "./pages/ProgramIndexPage";
import { ProgramPage } from "./pages/ProgramPage";

/**
 * Learn, 3rd entry: the program (week as calendar, list, progress; SPEC 3.4). The
 * route without an id opens the most recent one; the calendar uses the full shell width.
 */
export const programManifest: FeatureManifest = {
  id: "program",
  routes: [
    { path: "learn/programs", Component: ProgramIndexPage },
    { path: "learn/programs/:programId", Component: ProgramPage, handle: { wide: true } },
  ],
  nav: [
    { section: "learn", labelKey: "program.nav.program", path: "/learn/programs", order: 3 },
  ],
};
