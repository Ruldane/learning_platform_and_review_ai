import type { ProgramSummaryView } from "../viewTypes";
import { ProgramItem } from "./ProgramItem";

/** The user's programs, each linking to its page: state, start, weeks, progress. */
export function ProgramList({ programs }: { programs: ProgramSummaryView[] }) {
  return (
    <ul className="flex flex-col gap-3">
      {programs.map((program) => (
        <ProgramItem key={program.id} program={program} />
      ))}
    </ul>
  );
}
