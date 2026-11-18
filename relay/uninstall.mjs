// Retire le relais du démarrage et arrête celui qui tourne.
import { execSync } from "node:child_process";
import { rmSync } from "node:fs";
import { join } from "node:path";

const startup = join(
  process.env.APPDATA,
  "Microsoft",
  "Windows",
  "Start Menu",
  "Programs",
  "Startup",
  "tremplin-relay.vbs",
);
rmSync(startup, { force: true });
try {
  execSync(
    `powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name='node.exe'\\" | Where-Object { $_.CommandLine -like '*tremplin-relay.mjs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId }"`,
    { stdio: "ignore" },
  );
} catch {
  // aucun relais en cours
}
console.log("Relais retiré.");
