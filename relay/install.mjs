// Installe le relais au démarrage de la session Windows, fenêtre cachée (dossier Démarrage :
// sans droits d'administrateur), et le lance tout de suite. `node relay/uninstall.mjs` le retire.
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const startup = join(
  process.env.APPDATA,
  "Microsoft",
  "Windows",
  "Start Menu",
  "Programs",
  "Startup",
  "tremplin-relay.vbs",
);
const relay = join(here, "tremplin-relay.mjs");
const vbs = `CreateObject("WScript.Shell").Run """${process.execPath}"" ""${relay}""", 0, False\r\n`;
writeFileSync(startup, vbs);
spawn("wscript.exe", [startup], { detached: true, stdio: "ignore", windowsHide: true }).unref();
console.log(`Relais installé (${startup}) et lancé. Journal : %APPDATA%\\Tremplin\\relay.log`);
