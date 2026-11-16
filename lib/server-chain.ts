import { createClient, decodeLocalnetTransaction } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionHashVariant, type TransactionHash } from "genlayer-js/types";
import type { Bounty, Proof, Snapshot, TxView } from "./domain";
import { transactionState } from "./domain";
import source from "@/deploy/proof.json";

export const recorded = source as unknown as Proof;
const chain = createClient({
  chain: studionet,
  endpoint: "https://studio.genlayer.com/api",
});
const cache = new Map<string, { at: number; value: unknown }>();
const pending = new Map<string, Promise<unknown>>();

async function memo<T>(key: string, fn: () => Promise<T>, ttl = 30_000): Promise<T> {
  const old = cache.get(key);
  if (old && Date.now() - old.at < ttl) return old.value as T;
  const running = pending.get(key);
  if (running) return running as Promise<T>;
  const task = fn()
    .then((value) => {
      cache.set(key, { at: Date.now(), value });
      return value;
    })
    .finally(() => pending.delete(key));
  pending.set(key, task);
  return task;
}

export async function read<T>(method: string, args: unknown[] = []): Promise<T> {
  const address = recorded.contracts.BountyBoard?.address;
  if (!address) throw Error("The BountyBoard deployment is not recorded yet.");
  return memo(`board:${method}:${JSON.stringify(args)}`, async () => {
    const result = await chain.readContract({
      address: address as `0x${string}`,
      functionName: method,
      args: args as never[],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return (typeof result === "string" && /^[\[{]/.test(result)
      ? JSON.parse(result)
      : result) as T;
  });
}

export async function snapshot(): Promise<Snapshot> {
  const ids = await read<string[]>("get_bounty_ids", [0, 50]);
  const bounties: Bounty[] = [];
  for (const id of (ids ?? []).slice(-20).reverse()) {
    const [bounty, claims, balances, transactions] = await Promise.all([
      read<Bounty>("get_bounty", [id]),
      read<Bounty["claims"]>("get_claims", [id, 0, 50]),
      read<Bounty["balances"]>("get_balances", [id]),
      read<Bounty["transactions"]>("get_transaction_hashes", [id]),
    ]);
    bounties.push({ ...bounty, claims: claims ?? [], balances: balances ?? {}, transactions: transactions ?? [] });
  }
  return { bounties, readAt: new Date().toISOString(), network: "StudioNet", chainId: 61999 };
}

export async function transaction(hash: string): Promise<TxView> {
  if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) throw Error("Transaction hash is malformed.");
  return memo(`tx:${hash}`, async () => {
    const raw = await chain.request({ method: "eth_getTransactionByHash", params: [hash as TransactionHash] });
    if (!raw) return { hash, state: "SUBMITTED", children: [], appealDeadline: null, error: null };
    const receipt = decodeLocalnetTransaction(raw as never) as unknown as Record<string, unknown>;
    const state = transactionState(receipt);
    let appealDeadline: number | null = null;
    if (state === "ACCEPTED") {
      try {
        const window = Number(await chain.request({ method: "sim_getFinalityWindowTime" as never }));
        const starts = Number(receipt.timestamp_awaiting_finalization ?? 0);
        if (starts > 0 && window > 0 && receipt.leader_only === false && receipt.appealed !== true) {
          appealDeadline = starts + Number(receipt.appeal_processing_time ?? 0) + window * 0.8 ** Number(receipt.appeal_failed ?? 0);
        }
      } catch {
        appealDeadline = null;
      }
    }
    const leader = (receipt.consensus_data as { leader_receipt?: { result?: { payload?: { readable?: string } }; genvm_result?: { stderr?: string } }[] } | undefined)?.leader_receipt?.[0];
    return {
      hash,
      state,
      children: (receipt.triggered_transactions as string[]) ?? [],
      appealDeadline,
      error: state === "FINALIZED_ERROR" ? leader?.result?.payload?.readable ?? leader?.genvm_result?.stderr ?? "Open the transaction receipt for the execution error." : null,
    };
  }, 8_000);
}

export async function recordedStatus(): Promise<Proof> {
  return recorded;
}
