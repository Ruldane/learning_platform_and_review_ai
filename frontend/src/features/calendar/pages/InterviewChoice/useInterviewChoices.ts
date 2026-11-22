import { useQuery } from "@tanstack/react-query";
import { shortDay } from "@/shared/lib/format";
import { getApplications } from "../../api";

export function useInterviewChoices() {
  const query = useQuery({
    queryKey: ["calendar", "applications"],
    queryFn: ({ signal }) => getApplications(signal),
  });
  const dated = (query.data ?? []).flatMap((row) =>
    row.status === "interview" && row.interview_on
      ? [
          {
            id: row.id,
            label: [shortDay(row.interview_on), row.title, row.company].join(" · "),
          },
        ]
      : [],
  );
  return { query, dated };
}
