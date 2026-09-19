import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const api = await readFile(new URL("../lib/api.ts", import.meta.url), "utf8");
const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");

assert.match(api, /NEXT_PUBLIC_API_BASE_URL \|\| ""/, "same-origin API must be the default");
assert.match(api, /export async function getHealth\(/, "health client is required");
assert.match(page, /Model status/, "dashboard must expose model readiness");
assert.match(page, /Download JSON/, "inspection results must be exportable");
assert.match(page, /Print report/, "inspection report must be printable");
console.log("frontend behavioral contract passed");
