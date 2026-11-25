import { useState } from "react";
import { AdvancedSection } from "../../components/AdvancedSection";
import type { ProviderModels, SettingsOut } from "../../types";
import { AgentOverridesPanel } from "./AgentOverridesPanel";

interface AdvancedModeProps {
  settings: SettingsOut;
  providers: ProviderModels[];
}

/**
 * « Mode avancé » of Models and keys: one model per agent instead of its level's model.
 * Collapsed by default; agents are read only when it is opened.
 */
export function AdvancedMode({ settings, providers }: AdvancedModeProps) {
  const [open, setOpen] = useState(false);
  return (
    <AdvancedSection open={open} onToggle={() => setOpen((value) => !value)}>
      <AgentOverridesPanel settings={settings} providers={providers} />
    </AdvancedSection>
  );
}
