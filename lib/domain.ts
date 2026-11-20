export type TxState =
  | "SUBMITTED"
  | "PENDING"
  | "ACCEPTED"
  | "FINALIZED_SUCCESS"
  | "FINALIZED_ERROR";

export type Verdict = {
  criterion_index: number;
  criterion: string;
  verdict: "MET" | "NOT_MET" | "INSUFFICIENT_EVIDENCE";
  quote: string;
  reason: string;
  digest: string;
  evidence_class: string;
  recorded_at: number;
};

export type Claim = {
  id: string;
  bounty_id: string;
  hunter: string;
  head_sha: string;
  bond_wei: string;
  created_at: number;
  status: string;
  bond_status: string;
  identity_status?: string;
  reason: string;
  verdicts: Verdict[];
};

export type Bounty = {
  id: string;
  funder: string;
  repo: string;
  base_sha: string;
  title: string;
  criteria: string[];
  criteria_json: string;
  criteria_hash: string;
  criterion_specs: { kind: string; target: string; behavior: string }[];
  status: string;
  reason: string;
  rejection_reasons: string[];
  created_at: number;
  deadline: number;
  claim_bond_wei: string;
  reward_wei: string;
  reward_remaining_wei: string;
  queue_length: number;
  winner_id: string;
  close_cursor?: number;
  refund_cursor?: number;
  transactions: { action: string; hash: string }[];
  claims?: Claim[];
  balances?: Record<string, string>;
};

export type Snapshot = {
  bounties: Bounty[];
  readAt: string;
  network: "StudioNet";
  chainId: 61999;
  error?: string;
  stale?: boolean;
  staleSince?: string;
};

export type Proof = {
  network: string;
  chainId: number;
  explorer: string;
  releaseStatus: string;
  approvedTotalWei: number;
  contracts: Record<string, { address: string; source: string; sha256: string }>;
  transactions: Record<string, string>;
  cases: Record<string, Record<string, unknown>>;
  probeResults?: Record<string, unknown>;
  sourceCommit?: string | null;
  appUrl?: string | null;
  fixturesRepo?: string;
  scout?: { records?: Record<string, ScoutDraft> };
};

export type ScoutDraft = {
  id: string;
  repo: string;
  issue_number: number;
  requester: string;
  issue_title: string;
  issue_digest: string;
  status: "DRAFTED" | "UNACTIONABLE";
  criteria: string[];
  reason: string;
  created_at: number;
};

export type ScoutSnapshot = { drafts: ScoutDraft[]; readAt: string; error?: string; stale?: boolean };

export type TxView = {
  hash: string;
  state: TxState;
  children: string[];
  appealDeadline: number | null;
  error: string | null;
};

export function transactionState(r: Record<string, unknown>): TxState {
  const status = String(r.status_name ?? r.status ?? "SUBMITTED");
  if (status === "FINALIZED" || status === "7") {
    const consensus = r.consensus_data as
      | { leader_receipt?: { execution_result?: string }[] }
      | undefined;
    const execution = String(
      r.txExecutionResultName ??
        consensus?.leader_receipt?.[0]?.execution_result ??
        "",
    );
    return (
      ["SUCCESS", "FINISHED_WITH_RETURN"].includes(execution) ||
      (r.value_credited === true && String(r.type) === "0" && !r.consensus_data)
    ) && !["MAJORITY_DISAGREE", "DISAGREE"].includes(String(r.result_name))
      ? "FINALIZED_SUCCESS"
      : "FINALIZED_ERROR";
  }
  return status === "ACCEPTED" || status === "6"
    ? "ACCEPTED"
    : status === "SUBMITTED"
      ? "SUBMITTED"
      : "PENDING";
}

export const short = (value: string, left = 8, right = 6) =>
  value.length > left + right + 1
    ? `${value.slice(0, left)}…${value.slice(-right)}`
    : value;
