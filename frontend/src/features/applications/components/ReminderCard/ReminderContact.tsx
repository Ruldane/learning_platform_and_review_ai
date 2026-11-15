import { ExternalLink } from "lucide-react";
import { webUrl } from "@/shared/session-ui";
import { t } from "@/shared/i18n/t";
import type { ContactView } from "../viewTypes";

interface ReminderContactProps {
  contact: ContactView | null;
  linkedinSearchUrl: string | null;
}

/** Qui contacter : le contact (nom et rôle), ou, à défaut, une recherche LinkedIn dans un nouvel onglet. */
export function ReminderContact({ contact, linkedinSearchUrl }: ReminderContactProps) {
  const search = linkedinSearchUrl ? webUrl(linkedinSearchUrl) : null;
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-xs font-medium text-muted-foreground">
        {t("applications.reminder.contact")}
      </p>
      {contact ? (
        <p>
          {contact.role
            ? t("applications.reminder.contactNamed", { name: contact.name, role: contact.role })
            : contact.name}
        </p>
      ) : search ? (
        <a
          href={search.href}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex w-fit items-center gap-1 text-primary underline underline-offset-4"
        >
          {t("applications.reminder.searchLinkedin")}{" "}
          <span className="sr-only">{t("applications.reminder.newTab")}</span>
          <ExternalLink aria-hidden="true" className="size-3.5" />
        </a>
      ) : (
        <p className="text-muted-foreground">{t("applications.reminder.noContact")}</p>
      )}
    </div>
  );
}
