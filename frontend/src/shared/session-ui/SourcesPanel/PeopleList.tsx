import { t } from "@/shared/i18n/t";
import type { SourceView } from "../sourceTypes";
import { webUrl } from "../webUrl";
import { SourcesBlock } from "./SourcesBlock";

/**
 * « Praticiens repérés » (SPEC 10.3) : nom (lien vers le profil ou la publication), rôle et site
 * où la personne publie. Pas de note : ce ne sont pas des pages à citer.
 */
export function PeopleList({ people }: { people: SourceView[] }) {
  return (
    <SourcesBlock title={t("session.sources.people")} count={people.length}>
      <ul className="flex flex-col gap-2">
        {people.map((person) => {
          const address = webUrl(person.url);
          return (
            <li
              key={person.id}
              className="flex flex-col gap-0.5 rounded-lg border border-border bg-card px-3 py-2 text-sm"
            >
              <span className="font-medium break-words">
                {address ? (
                  <a
                    href={address.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline underline-offset-2 hover:text-primary"
                  >
                    {person.title}
                  </a>
                ) : (
                  person.title
                )}
              </span>
              {person.role ? (
                <span title={t("session.sources.peopleRole")}>{person.role}</span>
              ) : null}
              {address ? (
                <span className="text-xs break-all text-muted-foreground">
                  {t("session.sources.peoplePublishes", { host: address.hostname })}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </SourcesBlock>
  );
}
