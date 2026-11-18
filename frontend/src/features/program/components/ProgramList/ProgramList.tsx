import type { ProgramSummaryView } from "../viewTypes";
import { ProgramItem } from "./ProgramItem";

/** Les programmes de l'utilisatrice, chacun lien vers sa page : état, début, semaines, avancement. */
export function ProgramList({ programs }: { programs: ProgramSummaryView[] }) {
  return (
    <ul className="flex flex-col gap-3">
      {programs.map((program) => (
        <ProgramItem key={program.id} program={program} />
      ))}
    </ul>
  );
}
