import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

export function ConversationSearch({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm">
        {t("conversations.list.search")}
      </label>
      <input
        id={id}
        className={fieldClass}
        type="search"
        maxLength={120}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
