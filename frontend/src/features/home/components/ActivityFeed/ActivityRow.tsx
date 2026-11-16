import { Link } from "react-router";
import { fullDateTime, relativeTime } from "@/shared/lib/relativeTime";
import { t } from "@/shared/i18n/t";
import type { ActivityItemView } from "../viewTypes";
import { KindIcon } from "./KindIcon";

interface ActivityRowProps {
  item: ActivityItemView;
  now: Date;
}

/** Une ligne du fil : icône du genre, titre (lien vers l'écran concerné), détail et date relative. */
export function ActivityRow({ item, now }: ActivityRowProps) {
  const full = fullDateTime(item.at);
  return (
    <li className="flex gap-3 text-sm">
      <KindIcon kind={item.kind} />
      <div className="flex min-w-0 flex-1 flex-col">
        <span>
          <span className="sr-only">{t(`home.activity.kind.${item.kind}`)} : </span>
          {item.link ? (
            <Link to={item.link} className="text-primary underline underline-offset-4">
              {item.title}
            </Link>
          ) : (
            item.title
          )}
        </span>
        {item.detail ? <span className="text-muted-foreground">{item.detail}</span> : null}
        <time dateTime={item.at} title={full} className="text-xs text-muted-foreground">
          {relativeTime(item.at, now)}
          <span className="sr-only">, {full}</span>
        </time>
      </div>
    </li>
  );
}
