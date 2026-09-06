import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import {
  TrueForge,
  TrueForgeApi,
  isEventDelta,
  mergeEventDelta,
} from "@truefoundry/trueforge-sdk";

const AGENT_NAME = "trading-desk-sentinel";
const DEFAULT_ALERT =
  "OAA's paper account equity dropped noticeably in the last session. Investigate and report root cause.";

async function confirm(prompt: string): Promise<boolean> {
  const rl = createInterface({ input: stdin, output: stdout });
  const answer = (await rl.question(`${prompt} [y/N]: `)).trim().toLowerCase();
  rl.close();
  return answer === "y";
}

async function main() {
  const client = new TrueForge({
    baseUrl: process.env.TRUEFORGE_BASE_URL ?? "http://localhost:8790",
    timeoutInSeconds: 600,
  });

  const { data: session } = await client.sessions.create({ agent: { name: AGENT_NAME } });
  console.log(`Session ${session.id} opened against agent '${AGENT_NAME}'.\n`);

  const alert = process.env.ALERT ?? DEFAULT_ALERT;
  console.log(`Alert: ${alert}\n`);

  // Event handling mirrors ui/src/App.tsx's runTurn exactly — that version
  // was checked against the real @truefoundry/trueforge-sdk .d.ts files and
  // caught mistakes this file originally shared: tool calls only ever
  // arrive merged onto "model.message.delta" events (there is no standalone
  // "model.message" event), a call's tool name lives at `call.function.name`
  // not `call.toolInfo.name`, and a delta event's fragments (e.g. a tool
  // call's arguments streamed across several chunks) must be merged with
  // the SDK's own isEventDelta/mergeEventDelta helpers rather than just
  // keeping the last raw chunk, or a partially-streamed field gets lost.
  const events = new Map<string, TrueForgeApi.TurnStreamingEvent>();
  const pendingApprovals: TrueForgeApi.ToolApprovalRequiredEvent[] = [];

  const stream = await client.sessions.createTurnStream(session.id, {
    input: [{ type: "user.message", content: alert }],
  });

  for await (const { data: event } of stream.withMetadata()) {
    if (isEventDelta(event)) {
      const existing = events.get(event.id);
      if (existing) mergeEventDelta(existing, event);
      else events.set(event.id, event);
    } else {
      events.set(event.id, event);
    }

    if (event.type === "model.message.delta" && event.threadId === "main") {
      if (event.content) stdout.write(event.content);
      for (const call of event.toolCalls ?? []) {
        if (call.function?.name) {
          console.log(`\n[tool call] ${call.function.name} ${call.function.arguments ?? ""}`);
        }
      }
    }
    if (event.type === "tool.response") {
      console.log(`\n[tool result] ${event.toolCallId}: ${truncate(event.content)}`);
    }
    if (event.type === "tool.approval_required") {
      pendingApprovals.push(event);
    }
  }

  if (pendingApprovals.length === 0) {
    console.log("\n\nInvestigation finished — no irreversible action was proposed.");
    return;
  }

  console.log("\n\n=== APPROVAL REQUIRED ===");
  console.log("The agent proposed an irreversible action. Nothing has been sent to Alpaca yet.\n");

  const approvals: TrueForgeApi.UserToolApprovalEvent[] = [];
  for (const pending of pendingApprovals) {
    for (const ref of pending.toolCalls) {
      const source = events.get(ref.sourceEventId);
      if (source?.type !== "model.message.delta") continue;
      const call = source.toolCalls?.find((tc) => tc.id === ref.id);
      if (!call?.function?.name) continue;

      console.log(`Tool: ${call.function.name}`);
      console.log(`Args: ${call.function.arguments}\n`);
      const approved = await confirm("Approve this action?");

      approvals.push({
        type: "user.tool_approval",
        threadId: pending.threadId,
        toolCallId: ref.id,
        approval: approved
          ? { status: "allow" }
          : { status: "deny", reason: "denied via sentinel-client CLI" },
      });
    }
  }

  console.log(`\nResuming with ${approvals.filter((a) => a.approval.status === "allow").length} approved, ` +
    `${approvals.filter((a) => a.approval.status === "deny").length} denied...\n`);

  const resume = await client.sessions.createTurnStream(session.id, { input: approvals });
  for await (const { data: event } of resume.withMetadata()) {
    if (event.type === "model.message.delta" && event.threadId === "main") {
      stdout.write(event.content ?? "");
    }
    if (event.type === "turn.done") {
      console.log(`\n\nFinal status: ${event.state.status}`);
    }
  }
}

function truncate(s: string, n = 200): string {
  return s.length > n ? `${s.slice(0, n)}...` : s;
}

main().catch((err) => {
  console.error("sentinel-client failed:", err);
  process.exitCode = 1;
});