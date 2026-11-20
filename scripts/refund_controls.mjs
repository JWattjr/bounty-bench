// Live proof for the three refund controls, driven through the app's own write path.
// Every write calls `write()` from lib/wallet.ts (the function the buttons call) against an
// EIP-1193 bridge that signs with the ignored test keys in .env. Resumable: state lives in
// deploy/refund-controls.json and every hash is saved before waiting.
//
// usage: node scripts/refund_controls.mjs [rejected|closing|winner|all]
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { privateKeyToAccount } from "viem/accounts";
import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionHashVariant } from "genlayer-js/types";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RPC = "https://studio.genlayer.com/api";
const UA = "Mozilla/5.0 BountyBench/1.0";
const STATE_PATH = path.join(ROOT, "deploy/refund-controls.json");
const BOARD = JSON.parse(fs.readFileSync(path.join(ROOT, "deploy/proof.json"), "utf8")).contracts.BountyBoard.address;
const FIX = JSON.parse(fs.readFileSync(path.join(ROOT, "deploy/fixture.json"), "utf8"));
const REPO = FIX.repository;
const BASE = FIX.baseSha;
const FIX_HEAD = FIX.branches["hunter-d"]; // commit whose message carries Hunter D's Bounty-Claimant trailer
const CRITERION = "changes `normalize_slug` so that it collapses repeated hyphens";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

// ---- env and keys (never printed) -------------------------------------------------------
for (const raw of fs.readFileSync(path.join(ROOT, ".env"), "utf8").split(/\r?\n/)) {
  const line = raw.trim();
  if (!line || line.startsWith("#") || !line.includes("=")) continue;
  const i = line.indexOf("=");
  process.env[line.slice(0, i).trim()] ??= line.slice(i + 1).trim().replace(/^["']|["']$/g, "");
}
const keys = { funder: process.env.FUNDER_PRIVATE_KEY, hunterD: process.env.HUNTER_D_PRIVATE_KEY };

// ---- one global rate gate for every StudioNet request (30/min, 500/hr cap) --------------
let nextSlot = 0;
const realFetch = globalThis.fetch;
globalThis.fetch = async (input, init = {}) => {
  const url = typeof input === "string" ? input : input.url;
  if (!url.startsWith(RPC)) return realFetch(input, init);
  let method = "";
  try { method = JSON.parse(init.body ?? "{}").method ?? ""; } catch {}
  const safe = !method.startsWith("eth_send");
  for (let attempt = 0; attempt < (safe ? 5 : 1); attempt++) {
    const wait = Math.max(0, nextSlot - Date.now());
    nextSlot = Math.max(nextSlot, Date.now()) + 2600;
    if (wait) await sleep(wait);
    const headers = { ...(init.headers ?? {}), "User-Agent": UA };
    const res = await realFetch(input, { ...init, headers });
    if (!safe || ![429, 502, 503, 504].includes(res.status) || attempt === 4) return res;
    await sleep(8000 * (attempt + 1));
  }
};
const rpc = async (method, params = []) => {
  const res = await fetch(RPC, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
  const body = await res.json();
  if (body.error) throw Error(method + ": " + (body.error.message ?? JSON.stringify(body.error)));
  return body.result;
};

// ---- EIP-1193 bridge: what a browser wallet would do, signed by a test key --------------
const nonces = new Map();
const queues = new Map();
function bridgeFor(name) {
  const account = privateKeyToAccount(keys[name]);
  return {
    address: account.address,
    request: async ({ method, params = [] }) => {
      if (method === "eth_requestAccounts" || method === "eth_accounts") return [account.address];
      if (method === "eth_chainId") return "0xf22f";
      if (method === "wallet_switchEthereumChain") return null;
      if (method !== "eth_sendTransaction") return rpc(method, params);
      // serialize signing per key so concurrent clicks never reuse a nonce
      const prev = queues.get(name) ?? Promise.resolve();
      const job = prev.then(async () => {
        const tx = params[0];
        let nonce = nonces.get(name);
        if (nonce === undefined) nonce = Number(await rpc("eth_getTransactionCount", [account.address, "pending"]));
        const signed = await account.signTransaction({
          type: "legacy", chainId: 61999, nonce, gasPrice: 0n,
          gas: tx.gas ? BigInt(tx.gas) : 21000000n, to: tx.to, data: tx.data, value: BigInt(tx.value ?? "0x0"),
        });
        const hash = await rpc("eth_sendRawTransaction", [signed]);
        nonces.set(name, nonce + 1);
        return hash;
      });
      queues.set(name, job.catch(() => {}));
      try { return await job; } catch (e) { nonces.delete(name); throw e; }
    },
  };
}
const { write } = await import("../lib/wallet.ts");
async function appWrite(name, method, args, value = 0n) {
  globalThis.window = { ethereum: bridgeFor(name) }; // read synchronously by wallet.ts at call time
  return write(BOARD, method, args, BigInt(value));
}

// ---- reads -------------------------------------------------------------------------------
const reader = createClient({ chain: studionet, endpoint: RPC });
async function view(method, args = []) {
  const r = await reader.readContract({ address: BOARD, functionName: method, args, transactionHashVariant: TransactionHashVariant.LATEST_FINAL });
  return typeof r === "string" && /^[\[{]/.test(r) ? JSON.parse(r) : r;
}
const balance = async (name) => Number(BigInt(await rpc("eth_getBalance", [bridgeFor(name).address, "latest"])));

// ---- state -------------------------------------------------------------------------------
const state = fs.existsSync(STATE_PATH) ? JSON.parse(fs.readFileSync(STATE_PATH, "utf8")) : { cases: {}, transactions: {} };
const save = () => fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
const caseOf = (n) => (state.cases[n] ??= { name: n });

async function act(label, name, method, args, value = 0n) {
  if (!state.transactions[label]) {
    const hash = await appWrite(name, method, args, value);
    state.transactions[label] = hash;
    save();
    log(label, "SUBMITTED", hash);
  }
  return state.transactions[label];
}

async function finalTree(hash, label, depth = 0) {
  for (let i = 0; i < 400; i++) {
    const tx = await rpc("eth_getTransactionByHash", [hash]);
    const status = tx?.status_name ?? tx?.status;
    if (tx && ["FINALIZED", 7, "7"].includes(status)) {
      for (const [n, child] of (tx.triggered_transactions ?? []).entries()) {
        const childLabel = `${label}-child-${n}`;
        state.transactions[childLabel] ??= child;
        save();
        if (depth < 12) await finalTree(child, childLabel, depth + 1);
      }
      return tx;
    }
    if (tx && ["CANCELED", 8, "8"].includes(status)) { log(label, "CANCELED"); return tx; }
    await sleep(25000);
  }
  throw Error("still pending, rerun to resume: " + label);
}

async function bountyIdAfter(label) {
  const c = caseOf(label);
  if (c.bountyId) return c.bountyId;
  const ids = await view("get_bounty_ids", [0, 50]);
  c.bountyId = ids[ids.length - 1];
  save();
  return c.bountyId;
}

async function createBounty(caseName, title, criteria, reward, deadlineSeconds) {
  const c = caseOf(caseName);
  c.deadline ??= Math.floor(Date.now() / 1000) + deadlineSeconds;
  c.rewardWei = reward; c.claimBondWei = 1; c.criteria = criteria; save();
  const hash = await act(`${caseName}-create`, "funder", "create_bounty",
    [REPO, BASE, title, JSON.stringify(criteria), c.deadline, 1], BigInt(reward));
  await finalTree(hash, `${caseName}-create`);
  const id = await bountyIdAfter(caseName);
  log(caseName, "bounty", id, (await view("get_bounty", [id])).status);
  return id;
}

async function pollBounty(id, wanted, label, minutes = 120) {
  for (let i = 0; i < minutes; i++) {
    const b = await view("get_bounty", [id]);
    if (wanted.includes(b.status)) return b;
    if (i % 5 === 0) log(label, "waiting; status", b.status);
    await sleep(60000);
  }
  throw Error(label + ": never reached " + wanted.join("|"));
}

async function submitClaims(caseName, id, count) {
  const c = caseOf(caseName);
  c.claims ??= 0;
  while (c.claims < count) {
    const n = c.claims + 1;
    await act(`${caseName}-claim-${n}`, "hunterD", "claim", [id, FIX_HEAD], 1n);
    c.claims = n; save();
  }
  for (let i = 0; i < 180; i++) {
    const claims = await view("get_claims", [id, 0, 50]);
    const waiting = claims.filter((x) => x.status === "IDENTITY_CHECK_PENDING").length;
    log(caseName, `claims visible ${claims.length}/${count}, awaiting identity ${waiting}`);
    if (claims.length >= count && waiting === 0) return claims;
    await sleep(75000);
  }
  throw Error(caseName + ": claims did not settle into the queue");
}

// ---- cases ------------------------------------------------------------------------------
const creates = {
  rejected: () => createBounty("rejected", "Refund-control proof: deliberately vague bounty", ["make the code cleaner and well tested"], 15, 7200),
  closing: () => createBounty("closing", "Refund-control proof: repeated close over 21 pending claims", [CRITERION], 10, 6600),
  winner: () => createBounty("winner", "Refund-control proof: winner paid with 21 claims behind", [CRITERION], 10, 9000),
};
async function rejected() {
  const c = caseOf("rejected");
  const funderBefore = (c.funderBefore ??= await balance("funder"));
  const id = await creates.rejected();
  c.bountyId = id;
  let b = await view("get_bounty", [id]);
  if (b.status !== "SPEC_REJECTED" && b.status !== "REJECT_REFUND_PENDING" && b.status !== "REJECTED_REFUNDED") throw Error("expected a rejected spec, got " + b.status);
  c.statusBefore ??= b.status; save();
  const hash = await act("rejected-refund_rejected", "funder", "refund_rejected", [id]);
  await finalTree(hash, "rejected-refund_rejected");
  b = await pollBounty(id, ["REJECTED_REFUNDED"], "rejected");
  c.statusAfter = b.status; c.rewardRemainingAfter = b.reward_remaining_wei;
  c.funderBefore = funderBefore; c.funderAfter = await balance("funder"); c.done = true; save();
  log("rejected DONE", c.statusBefore, "->", c.statusAfter);
}

async function closing() {
  const c = caseOf("closing");
  const id = await creates.closing();
  c.bountyId = id;
  const claims = await submitClaims("closing", id, 21);
  c.pendingBeforeClose = claims.filter((x) => x.status === "PENDING").length; save();
  log("closing waiting for deadline + grace");
  const ready = c.deadline + 1800 + 120;
  while (Math.floor(Date.now() / 1000) < ready) await sleep(30000);
  let h = await act("closing-close-1", "hunterD", "close", [id]);
  await finalTree(h, "closing-close-1");
  let b = await pollBounty(id, ["CLOSING"], "closing");
  c.afterFirstClose = { status: b.status, closeCursor: b.close_cursor }; save();
  log("closing after first close", c.afterFirstClose);
  h = await act("closing-close-2", "hunterD", "close", [id]);
  await finalTree(h, "closing-close-2");
  b = await pollBounty(id, ["CLOSED"], "closing");
  const after = await view("get_claims", [id, 0, 50]);
  c.statusAfter = b.status; c.claimsRefunded = after.filter((x) => x.bond_status === "REFUNDED").length;
  c.rewardRemainingAfter = b.reward_remaining_wei; c.done = true; save();
  log("closing DONE", c.statusAfter, "refunded", c.claimsRefunded, "of", after.length);
}

async function winner() {
  const c = caseOf("winner");
  const id = await creates.winner();
  c.bountyId = id;
  const claims = await submitClaims("winner", id, 22);
  c.claimsQueued = claims.length; save();
  const judge = await act("winner-judge-1", "hunterD", "judge_next", [id]);
  await finalTree(judge, "winner-judge-1");
  let b = await pollBounty(id, ["WINNER_REFUNDS_PENDING", "CLOSED"], "winner");
  c.afterWin = { status: b.status, refundCursor: b.refund_cursor, winner: b.winner_id }; save();
  log("winner after win", c.afterWin);
  if (b.status !== "CLOSED") {
    const h = await act("winner-refund_pending-1", "hunterD", "refund_pending", [id]);
    await finalTree(h, "winner-refund_pending-1");
    b = await pollBounty(id, ["CLOSED"], "winner");
  }
  const after = await view("get_claims", [id, 0, 50]);
  c.statusAfter = b.status;
  c.claimsRefunded = after.filter((x) => x.bond_status === "REFUNDED").length;
  c.claimsPaid = after.filter((x) => x.bond_status === "PAID").length;
  c.done = true; save();
  log("winner DONE", c.statusAfter, "refunded", c.claimsRefunded, "paid", c.claimsPaid);
}

const which = process.argv[2] ?? "all";
const jobs = { rejected, closing, winner };
if (which === "all") {
  // create sequentially so each bounty id is unambiguous, then run the long waits together
  for (const name of ["rejected", "closing", "winner"]) await creates[name]();
}
const run = which === "all" ? Object.values(jobs) : [jobs[which]];
await Promise.all(run.map((fn) => fn()));
log("finished", which);
