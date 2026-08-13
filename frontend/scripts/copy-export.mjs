// Copies the Next static export into backend/static/, which FastAPI serves at /.
// Used for local runs; the Docker build copies out/ across stages itself.
import { cpSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(frontendDir, "out");
const target = resolve(frontendDir, "..", "backend", "static");

rmSync(target, { recursive: true, force: true });
cpSync(source, target, { recursive: true });
// Keeps the directory in git, so the static mount has somewhere to point on a fresh clone.
writeFileSync(resolve(target, ".gitkeep"), "");
console.log(`Copied ${source} -> ${target}`);
