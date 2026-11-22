import { useParams } from "react-router";
import { ClassroomThread } from "./ClassroomThread";

export function ClassroomPage() {
  const { lessonId = "" } = useParams();
  return <ClassroomThread key={lessonId} lessonId={lessonId} />;
}
