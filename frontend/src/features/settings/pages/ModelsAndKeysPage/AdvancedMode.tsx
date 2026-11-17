import { useState } from "react";
import { AdvancedSection } from "../../components/AdvancedSection";
import type { ProviderModels, SettingsOut } from "../../types";
import { AgentOverridesPanel } from "./AgentOverridesPanel";

interface AdvancedModeProps {
  settings: SettingsOut;
  providers: ProviderModels[];
}

/**
 * « Mode avancé » de Modèles et clés : un modèle par agent à la place de celui de son niveau.
 * Replié par défaut ; les agents ne sont lus qu'à l'ouverture.
 */
export function AdvancedMode({ settings, providers }: AdvancedModeProps) {
  const [open, setOpen] = useState(false);
  return (
    <AdvancedSection open={open} onToggle={() => setOpen((value) => !value)}>
      <AgentOverridesPanel settings={settings} providers={providers} />
    </AdvancedSection>
  );
}
