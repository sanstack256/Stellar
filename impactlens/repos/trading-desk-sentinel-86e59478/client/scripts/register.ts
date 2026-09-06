
import { TrueForge } from "@truefoundry/trueforge-sdk";
import { readFile } from "node:fs/promises";
import { resolveMcpUrl } from "./resolve-mcp-url.js";

const client = new TrueForge({
  baseUrl: process.env.TRUEFORGE_BASE_URL ?? "http://localhost:8790",
});

function requireSkillRepoUrl(): string {
  const url = process.env.SKILL_REPO_URL;
  if (!url) {
    throw new Error(
      "SKILL_REPO_URL is not set. The skill is git-backed, so TrueForge needs " +
      "the real, pushed URL of this repo (e.g. https://github.com/<org>/trading-desk-sentinel) " +
      "— set SKILL_REPO_URL before running register.ts, or the agent will load no playbook at all.",
    );
  }
  if (url.includes("<") || url.includes(">")) {
    throw new Error(`SKILL_REPO_URL looks like an unfilled placeholder: "${url}". Set it to the real repo URL.`);
  }
  return url;
}

async function main() {
  const sharedSecret = process.env.MCP_SHARED_SECRET;

  await client.settings.mcpServers.createOrUpdate({
    manifest: {
      name: "sentinel-alpaca-mcp",
      type: "remote",
      url: resolveMcpUrl(),
      description:
        "OAA's paper-trading account: read-only account/positions/orders/history, plus " +
        "destructive flatten_position and disable_strategy (approval-gated).",
      ...(sharedSecret && {
        auth: { type: "header", headers: { Authorization: `Bearer ${sharedSecret}` } },
      }),
    },
  });
  console.log("Registered MCP connector: sentinel-alpaca-mcp");

  await client.settings.skills.createOrUpdate({
    manifest: {
      name: "trading-incident-response",
      type: "git",
      url: requireSkillRepoUrl(),
      ref: process.env.SKILL_REPO_REF ?? "main",
      path: "skills/trading-incident-response",
      description:
        "Playbook for investigating an OAA account anomaly before proposing any irreversible action.",
    },
  });
  console.log("Registered skill: trading-incident-response");


  const spec = JSON.parse(
    await readFile(new URL("../../agent/trading-desk-sentinel.json", import.meta.url), "utf8"),
  );
  const { data: agent } = await client.agents.create(spec);
  console.log(`Registered agent: ${agent.name} (id: ${agent.id})`);
}

main().catch((err) => {
  console.error("register.ts failed:", err);
  process.exitCode = 1;
});
