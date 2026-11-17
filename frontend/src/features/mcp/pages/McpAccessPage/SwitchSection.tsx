import { errorMessage } from "@/shared/api/errors";
import { InlineError } from "@/shared/ui/states/InlineError";
import { McpSwitch } from "../../components/McpSwitch";
import { useSetMcpEnabled } from "../../hooks/useSetMcpEnabled";

/** L'interrupteur général ; une écriture ratée se dit sous l'interrupteur, qui reste où il était. */
export function SwitchSection({ enabled }: { enabled: boolean }) {
  const setEnabled = useSetMcpEnabled();
  return (
    <div className="flex flex-col gap-3">
      <McpSwitch
        enabled={enabled}
        pending={setEnabled.isPending}
        onChange={(next) => setEnabled.mutate(next)}
      />
      {setEnabled.isError ? <InlineError message={errorMessage(setEnabled.error)} /> : null}
    </div>
  );
}
