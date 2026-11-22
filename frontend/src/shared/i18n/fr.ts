import { account } from "./messages/account";
import { agents } from "./messages/agents";
import { applications } from "./messages/applications";
import { appMessages } from "./messages/app";
import { auth } from "./messages/auth";
import { book } from "./messages/book";
import { boss } from "./messages/boss";
import { brain } from "./messages/brain";
import { calendar } from "./messages/calendar";
import { capture } from "./messages/capture";
import { chat } from "./messages/chat";
import { concentration } from "./messages/concentration";
import { conversations } from "./messages/conversations";
import { codeTrial } from "./messages/codeTrial";
import { compatibleOffers } from "./messages/compatibleOffers";
import { contributions } from "./messages/contributions";
import { costs } from "./messages/costs";
import { cv } from "./messages/cv";
import { demo } from "./messages/demo";
import { expertDebates } from "./messages/expertDebates";
import { feynman } from "./messages/feynman";
import { futureSelf } from "./messages/futureSelf";
import { galaxy } from "./messages/galaxy";
import { gradeAppeals } from "./messages/gradeAppeals";
import { gap } from "./messages/gap";
import { ghost } from "./messages/ghost";
import { home } from "./messages/home";
import { ide } from "./messages/ide";
import { learning } from "./messages/learning";
import { lessonHunt } from "./messages/lessonHunt";
import { lessonVariants } from "./messages/lessonVariants";
import { lessonUpdates } from "./messages/lessonUpdates";
import { lessons } from "./messages/lessons";
import { linkedInDrafts } from "./messages/linkedInDrafts";
import { blindAssessment } from "./messages/blindAssessment";
import { interprogramPlanning } from "./messages/interprogramPlanning";
import { meetingModules } from "./messages/meetingModules";
import { datedCommitments } from "./messages/datedCommitments";
import { dataInvestigation } from "./messages/dataInvestigation";
import { incidentReplay } from "./messages/incidentReplay";
import { proofPackets } from "./messages/proofPackets";
import { missions } from "./messages/missions";
import { decisionLab } from "./messages/decisionLab";
import { routines } from "./messages/routines";
import { contradictoryWatch } from "./messages/contradictoryWatch";
import { errorAtlas } from "./messages/errorAtlas";
import { skillTransfer } from "./messages/skillTransfer";
import { mcp } from "./messages/mcp";
import { mentorReviews } from "./messages/mentorReviews";
import { memory } from "./messages/memory";
import { messageReview } from "./messages/messageReview";
import { mobile } from "./messages/mobile";
import { onboarding } from "./messages/onboarding";
import { offerComparison } from "./messages/offerComparison";
import { oncall } from "./messages/oncall";
import { paperLab } from "./messages/paperLab";
import { podcast } from "./messages/podcast";
import { portfolio } from "./messages/portfolio";
import { program } from "./messages/program";
import { projectHandoffs } from "./messages/projectHandoffs";
import { projects } from "./messages/projects";
import { quiz } from "./messages/quiz";
import { radar } from "./messages/radar";
import { reading } from "./messages/reading";
import { recruitmentProcess } from "./messages/recruitmentProcess";
import { replan } from "./messages/replan";
import { research } from "./messages/research";
import { session } from "./messages/session";
import { settings } from "./messages/settings";
import { skillMarket } from "./messages/skillMarket";
import { skills } from "./messages/skills";
import { studyReturn } from "./messages/studyReturn";
import { study } from "./messages/study";
import { systemDesign } from "./messages/systemDesign";
import { surpriseInterview } from "./messages/surpriseInterview";
import { voice } from "./messages/voice";
import { training } from "./messages/training";

/**
 * Tous les textes de l'interface, en français : agrégat des fichiers `messages/<zone>.ts`.
 * Règle : une nouvelle feature ajoute un fichier `messages/<feature>.ts` (`export const <feature>
 * = { … } as const;`) et une ligne ici. `{nom}` marque une variable (voir `t`).
 */
export const fr = {
  ...appMessages,
  systemDesign,
  auth,
  brain,
  book,
  boss,
  account,
  calendar,
  session,
  agents,
  demo,
  settings,
  onboarding,
  memory,
  mentorReviews,
  mobile,
  messageReview,
  research,
  program,
  lessonHunt,
  lessonUpdates,
  lessonVariants,
  lessons,
  learning,
  study,
  studyReturn,
  surpriseInterview,
  voice,
  training,
  oncall,
  offerComparison,
  paperLab,
  podcast,
  portfolio,
  ghost,
  quiz,
  skillMarket,
  skills,
  replan,
  recruitmentProcess,
  capture,
  chat,
  concentration,
  conversations,
  compatibleOffers,
  contributions,
  codeTrial,
  gap,
  gradeAppeals,
  costs,
  cv,
  applications,
  home,
  radar,
  expertDebates,
  feynman,
  futureSelf,
  galaxy,
  reading,
  projects,
  projectHandoffs,
  linkedInDrafts,
  missions,
  proofPackets,
  incidentReplay,
  dataInvestigation,
  datedCommitments,
  meetingModules,
  blindAssessment,
  interprogramPlanning,
  decisionLab,
  routines,
  skillTransfer,
  errorAtlas,
  contradictoryWatch,
  mcp,
  ide,
} as const;
