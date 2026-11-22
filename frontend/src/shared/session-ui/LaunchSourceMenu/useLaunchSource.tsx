import { useState } from "react";
import type { RunSource } from "@/shared/lib/runSource";
import { LaunchSourceMenu } from "./LaunchSourceMenu";

/** Le choix local vit avec le formulaire, et le défaut continue de suivre le menu global. */
export function useLaunchSource() {
  const [source, setSource] = useState<RunSource>();
  return { source, menu: <LaunchSourceMenu value={source} onChange={setSource} /> };
}
