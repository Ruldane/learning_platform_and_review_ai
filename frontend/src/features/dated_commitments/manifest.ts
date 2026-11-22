import type { FeatureManifest } from "@/shared/lib/feature";
import { commitmentsPath } from "./format";
import { CommitmentsPage } from "./pages/CommitmentsPage";
import { CommitmentDetailPage } from "./pages/CommitmentDetailPage";

export const datedCommitmentsManifest: FeatureManifest = {
  id: "dated_commitments",
  routes: [
    { path: "etudier/engagements", Component: CommitmentsPage },
    { path: "etudier/engagements/:commitmentId", Component: CommitmentDetailPage },
  ],
  nav: [
    { section: "study", labelKey: "datedCommitments.title", path: commitmentsPath, order: 3.85 },
  ],
};
