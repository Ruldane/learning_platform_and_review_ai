import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { MarketFilters } from "../../types";

interface Props {
  role: string;
  zone: string;
  apply: (filters: MarketFilters) => void;
}

export function MarketFilter({ role, zone, apply }: Props) {
  const [editedRole, setRole] = useState(role);
  const [editedZone, setZone] = useState(zone);
  const fields = [
    { key: "role", label: t("skillMarket.role"), value: editedRole, set: setRole },
    { key: "zone", label: t("skillMarket.zone"), value: editedZone, set: setZone },
  ];
  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-end"
      onSubmit={(event) => {
        event.preventDefault();
        if (editedRole.trim().length >= 2 && editedZone.trim().length >= 2) {
          apply({ role: editedRole.trim(), zone: editedZone.trim() });
        }
      }}
    >
      {fields.map(({ key, label, value, set }) => (
        <label key={key} className="flex min-w-0 flex-1 flex-col gap-1 text-sm font-medium">
          {label}
          <input
            value={value}
            onChange={(event) => set(event.target.value)}
            minLength={2}
            maxLength={120}
            required
            className="rounded-md border border-input bg-background p-2 focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
      ))}
      <Button type="submit">{t("skillMarket.filter")}</Button>
    </form>
  );
}
