import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { committeePath, interviewPath, kitPath } from "../../urls";
import { DrawerSection } from "./DrawerSection";

/** Links to the kit, the practice interview and the committee of this application. */
interface Props {
  applicationId: string;
  hasScheduledInterview?: boolean;
}

export function ToolLinks({ applicationId, hasScheduledInterview }: Props) {
  const links = [
    { to: kitPath(applicationId), label: t("applications.drawer.kit") },
    { to: interviewPath(applicationId), label: t("applications.drawer.interview") },
    { to: committeePath(applicationId), label: t("applications.drawer.committee") },
  ];
  if (hasScheduledInterview) {
    links.push({
      to: `/settings/calendar?application=${encodeURIComponent(applicationId)}`,
      label: t("calendar.link"),
    });
  }
  return (
    <DrawerSection title={t("applications.drawer.toolsTitle")}>
      <ul className="flex flex-wrap gap-2">
        {links.map((link) => (
          <li key={link.to}>
            <Link to={link.to} className={buttonVariants({ variant: "outline" })}>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </DrawerSection>
  );
}
