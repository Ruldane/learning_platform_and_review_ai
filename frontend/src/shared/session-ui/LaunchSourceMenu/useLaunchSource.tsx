import { useState } from "react";
import type { RunSource } from "@/shared/lib/runSource";
import { LaunchSourceMenu } from "./LaunchSourceMenu";

/** The local choice lives with the form, and the default keeps following the global menu. */
export function useLaunchSource() {
  const [source, setSource] = useState<RunSource>();
  return { source, menu: <LaunchSourceMenu value={source} onChange={setSource} /> };
}
