"use client";

import { ArrowLeft, ArrowUpRight, ExternalLink, FileCode2, GitBranch, ShieldCheck, Wallet } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Bounty, Proof, Snapshot, TxState, TxView } from "@/lib/domain";
import { short } from "@/lib/domain";
import { walletAccount, write } from "@/lib/wallet";

const EXPLORER = "https://explorer-studio.genlayer.com";

function timeLabel(seconds: number) {
  const delta = seconds - Math.floor(Date.now() / 1000);
  if (delta <= 0) return "Deadline passed";
  const hours = Math.floor(delta / 3600);
  const minutes = Math.floor((delta % 3600) / 60);
  return hours >= 24 ? `${Math.floor(hours / 24)}d ${hours % 24}h` : `${hours}h ${minutes}m`;
}

function stateTone(status: string) {
  if (["OPEN", "WON", "CLOSED", "MET", "FINALIZED_SUCCESS"].includes(status)) return "tone-good";
  if (["COMPILING", "PENDING", "JUDGING", "ACCEPTED", "AWARD_PENDING", "SUBMITTED"].includes(status)) return "tone-wait";
  if (["FAILED", "IDENTITY_MISMATCH", "NOT_MET", "SPEC_REJECTED", "FINALIZED_ERROR"].includes(status)) return "tone-bad";
  return "tone-neutral";
}

function NativeTx({ hash }: { hash: string }) {
  const [view, setView] = useState<TxView | null>(null);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const response = await fetch(`/api/transactions/${hash}`, { cache: "no-store" });
        const value = await response.json() as TxView;
        if (!active || !response.ok) return;
        setView(value);
        if (!["FINALIZED_SUCCESS", "FINALIZED_ERROR"].includes(value.state)) timer = setTimeout(poll, 5_000);
      } catch { if (active) timer = setTimeout(poll, 8_000); }
    };
    void poll();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [hash]);
  const state: TxState = view?.state ?? "SUBMITTED";
  const appeal = view?.appealDeadline ? `${timeLabel(view.appealDeadline)} in native appeal window` : state.startsWith("FINALIZED") ? "Finalized; native appeal window ended" : "Appeal timing appears while accepted";
  return <span className="native-state"><span className={`status-tag ${stateTone(state)}`}>{state.replaceAll("_", " ")}</span><small>{appeal}</small></span>;
}

export default function BountyDetail({ bountyId, proof }: { bountyId: string; proof: Proof }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadError, setLoadError] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [account, setAccount] = useState("");
  const [headSha, setHeadSha] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [activity, setActivity] = useState<{ hash: string; title: string; state: TxState; error?: string | null }[]>([]);
  const boardAddress = proof.contracts.BountyBoard?.address ?? "";

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/live", { cache: "no-store" });
      const value = await response.json() as Snapshot;
      setSnapshot(value);
      setLoadError(value.error ?? "");
    } catch (error) { setLoadError(error instanceof Error ? error.message : "StudioNet read failed."); }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 25_000);
    return () => clearInterval(timer);
  }, [refresh]);

  const bounty = snapshot?.bounties.find((item) => item.id === bountyId) as Bounty | undefined;
  const claims = bounty?.claims ?? [];
  const selected = claims.find((item) => item.id === selectedId) ?? claims[0];
  const criteriaResults = (bounty as (Bounty & { spec_results?: { accepted: boolean; reason: string }[] }) | undefined)?.spec_results ?? [];
  const transactionMap = useMemo(() => new Map((bounty?.transactions ?? []).map((item) => [item.action, item.hash])), [bounty?.transactions]);

  async function connect() {
    setActionError("");
    try { setAccount((await walletAccount()).account); }
    catch (error) { setActionError(error instanceof Error ? error.message : "Wallet connection failed."); }
  }

  async function submit(title: string, method: string, args: unknown[], value = BigInt(0)) {
    if (!boardAddress) { setActionError("The Board address is missing from the proof manifest."); return; }
    setBusy(true); setActionError("");
    try {
      const hash = await write(boardAddress, method, args, value);
      setActivity((items) => [{ hash, title, state: "SUBMITTED" }, ...items]);
      void refresh();
      if (!account) setAccount((await walletAccount()).account);
    } catch (error) { setActionError(error instanceof Error ? error.message : `${title} failed.`); }
    finally { setBusy(false); }
  }

  const onState = useCallback((hash: string, state: TxState, error?: string | null) => {
    setActivity((items) => items.map((item) => item.hash === hash ? { ...item, state, error } : item));
  }, []);

  if (!snapshot && !loadError) return <main className="shell"><div className="loading-state">Reading the finalized StudioNet board…</div></main>;
  if (!bounty) return <main className="shell"><header className="topbar"><Link className="brand-lockup" href="/"><span className="brand-mark">BB</span><span>Bounty Bench</span></Link><span className="network-chip"><i /> StudioNet <b>61999</b></span></header><section className="not-found panel"><h1>{loadError ? "Live read unavailable" : "Bounty not found"}</h1><p>{loadError || `No finalized bounty with id ${bountyId} was returned by the Board.`}</p><Link className="text-link" href="/"><ArrowLeft size={14} /> Back to board</Link></section></main>;

  return <main className="shell">
    <header className="topbar">
      <Link className="brand-lockup" href="/"><span className="brand-mark">BB</span><span>Bounty Bench</span></Link>
      <nav className="topnav"><Link href="/">Board</Link><a className="nav-active" href="#claims">Bounty review</a></nav>
      <div className="topbar-right"><span className="network-chip"><i /> StudioNet <b>61999</b></span><span className="read-state"><span className="pulse-dot" /> Live read</span><button className="button button-quiet" onClick={connect}><Wallet size={14} /> {account ? short(account) : "Connect wallet"}</button></div>
    </header>

    <div className="breadcrumb"><Link href="/"><ArrowLeft size={14} /> Bounty queue</Link><span>/</span><span className="mono">{bounty.id}</span><span className={`status-tag ${stateTone(bounty.status)}`}>{bounty.status.replaceAll("_", " ")}</span></div>
    <section className="case-heading">
      <div><div className="repo-line"><GitBranch size={14} /><a href={`https://github.com/${bounty.repo}`} target="_blank" rel="noreferrer">{bounty.repo} <ExternalLink size={12} /></a><span>·</span><span>Base <code>{short(bounty.base_sha, 10, 8)}</code></span></div><h1>{bounty.title}</h1><p>Queue order is fixed at claim submission. Validators judge one frozen criterion at a time.</p></div>
      <div className="case-reward"><span>ESCROWED REWARD</span><strong>{bounty.reward_wei}<small> wei</small></strong><span>{timeLabel(bounty.deadline)} left</span></div>
    </section>

    <div className="detail-grid">
      <div className="detail-main">
        <section className="panel criteria-panel">
          <div className="panel-heading"><div><h2>Frozen acceptance criteria</h2><p>Hash stored when the bounty opened · {bounty.criteria.length} checks</p></div><span className="criteria-seal"><ShieldCheck size={15} /> {bounty.criteria_hash.slice(0, 10)}</span></div>
          <div className="criteria-list">{bounty.criteria.map((criterion, index) => {
            const spec = bounty.criterion_specs?.[index];
            const result = criteriaResults[index];
            return <div className="criterion-row" key={criterion}><span className="criterion-index">{String(index + 1).padStart(2, "0")}</span><div className="criterion-body"><strong>{criterion}</strong><small>{spec ? `${spec.kind} · ${spec.target}` : result?.reason ?? "Awaiting spec compilation"}</small></div><span className={`status-tag ${result ? result.accepted ? "tone-good" : "tone-bad" : "tone-neutral"}`}>{result ? result.accepted ? "FROZEN" : "REJECTED" : "FROZEN"}</span></div>;
          })}</div>
          <div className="hash-row"><span>CRITERIA SHA-256</span><code>{bounty.criteria_hash}</code></div>
          {bounty.reason && <p className="case-reason">{bounty.reason}</p>}
        </section>

        <section className="panel queue-panel" id="claims">
          <div className="panel-heading"><div><h2>Claim queue</h2><p>{claims.length} submitted · ordered by Board storage</p></div><span className="queue-count-large">{String(claims.length).padStart(2, "0")}</span></div>
          {claims.length === 0 ? <div className="empty-line">No claims yet. The first payable claim enters position 01.</div> : <div className="claim-table">
            <div className="claim-head"><span>POS / HUNTER</span><span>COMMIT</span><span>IDENTITY</span><span>CLAIM STATE</span></div>
            {claims.map((claim, index) => <button key={claim.id} className={`claim-row ${selected?.id === claim.id ? "claim-selected" : ""}`} onClick={() => setSelectedId(claim.id)}>
              <span className="claim-who"><span className="serial">{String(index + 1).padStart(2, "0")}</span><span><strong>{claim.id}</strong><small>{short(claim.hunter, 7, 5)}</small></span></span>
              <code>{short(claim.head_sha, 9, 7)}</code><span className={`identity-state ${claim.identity_status === "MATCH" ? "tone-good" : claim.identity_status === "MISMATCH" ? "tone-bad" : "tone-neutral"}`}>{claim.identity_status ?? "CHECKING"}</span><span className={`status-tag ${stateTone(claim.status)}`}>{claim.status.replaceAll("_", " ")}</span>
            </button>)}
          </div>}
          <p className="panel-note"><ShieldCheck size={13} /> The trailer check compares the commit’s Bounty-Claimant line with the sending address. It is a demo anti-copy rule, not legal identity verification.</p>
        </section>

        {selected && <section className="panel evidence-panel">
          <div className="panel-heading"><div><h2>Claim evidence</h2><p>{selected.id} <span>·</span> bond {selected.bond_wei} wei · {selected.bond_status.replaceAll("_", " ")}</p></div><a className="button button-quiet" href={`https://github.com/${bounty.repo}/compare/${bounty.base_sha}...${selected.head_sha}.diff`} target="_blank" rel="noreferrer"><FileCode2 size={14} /> Open pinned diff <ArrowUpRight size={13} /></a></div>
          {selected.reason && <div className="reason-strip">{selected.reason}</div>}
          {selected.verdicts.length === 0 ? <div className="empty-line">No criterion verdict has finalized for this claim.</div> : <div className="verdict-list">{selected.verdicts.map((verdict) => {
            const letter = selected.id.match(/^claim-(\d+)$/)?.[1] ? "ABCDE"[Number(selected.id.match(/^claim-(\d+)$/)?.[1]) - 1] : "";
            const action = letter ? `judge:judge-${letter}-c${verdict.criterion_index}` : "";
            const hash = action ? transactionMap.get(action) : undefined;
            return <article className="verdict-row" key={`${selected.id}-${verdict.criterion_index}`}>
              <div className="verdict-top"><span className="criterion-index">{String(verdict.criterion_index + 1).padStart(2, "0")}</span><strong>{verdict.criterion}</strong><span className={`status-tag ${stateTone(verdict.verdict)}`}>{verdict.verdict.replaceAll("_", " ")}</span></div>
              {verdict.quote && <blockquote className="diff-quote"><span>VALIDATOR QUOTE</span><code>{verdict.quote}</code></blockquote>}
              <p className="verdict-reason">{verdict.reason}</p>
              <div className="evidence-meta"><span><small>DIFF SHA-256</small><code>{verdict.digest || "No diff digest"}</code></span><span><small>EVIDENCE</small><strong>{verdict.evidence_class}</strong></span>{hash && <span><small>NATIVE APPEAL</small><NativeTx hash={hash} /></span>}</div>
              {hash && <a className="text-link" href={`${EXPLORER}/tx/${hash}`} target="_blank" rel="noreferrer">Judgment transaction {short(hash)} <ExternalLink size={12} /></a>}
              <a className="source-link" href={`https://github.com/${bounty.repo}/compare/${bounty.base_sha}...${selected.head_sha}.diff`} target="_blank" rel="noreferrer">View source diff <ExternalLink size={12} /></a>
            </article>;
          })}</div>}
        </section>}
      </div>

      <aside className="detail-side">
        <section className="panel action-panel">
          <div className="panel-heading"><div><h2>Wallet actions</h2><p>Writes are sent from your connected EIP-1193 wallet.</p></div><span className="action-mark"><Wallet size={15} /></span></div>
          <label className="action-label">Commit SHA<input className="mono-input" value={headSha} onChange={(event) => setHeadSha(event.target.value)} placeholder="40 hexadecimal characters" /></label>
          <button className="button button-primary full-width" disabled={busy || !/^[0-9a-f]{40}$/i.test(headSha) || bounty.status !== "OPEN"} onClick={() => void submit("Submit claim", "claim", [bounty.id, headSha.trim()], BigInt(bounty.claim_bond_wei))}>{busy ? "Waiting for wallet…" : `Submit claim · ${bounty.claim_bond_wei} wei bond`}</button>
          <button className="button button-secondary full-width" disabled={busy || bounty.status !== "OPEN"} onClick={() => void submit("Judge next criterion", "judge_next", [bounty.id])}>Judge next criterion</button>
          <button className="button button-secondary full-width" disabled={busy || bounty.status !== "OPEN" || Date.now() / 1000 < bounty.deadline + 1800} onClick={() => void submit("Close bounty", "close", [bounty.id])}>Close after deadline + grace</button>
          <p className="form-note"><ShieldCheck size={13} /> Only claims with finalized identity checks can enter judgment. The claim order cannot be edited.</p>
          {actionError && <p className="form-error">{actionError}</p>}
        </section>

        <section className="panel balance-panel">
          <div className="panel-heading"><div><h2>Settlement ledger</h2><p>Contract view · wei amounts</p></div></div>
          <div className="balance-row"><span>Reward remaining</span><strong>{bounty.reward_remaining_wei}</strong></div>
          <div className="balance-row"><span>Held claim bonds</span><strong>{bounty.balances?.claim_bonds_held_wei ?? "—"}</strong></div>
          <div className="balance-row"><span>Forfeited bonds</span><strong>{bounty.balances?.forfeited_bonds_wei ?? "—"}</strong></div>
          {bounty.winner_id && <div className="balance-winner"><span>WINNER</span><strong>{bounty.winner_id}</strong></div>}
        </section>

        <section className="panel tx-panel">
          <div className="panel-heading"><div><h2>On-chain trail</h2><p>Hashes stored by the Board, no indexer.</p></div></div>
          {(bounty.transactions ?? []).length === 0 ? <div className="empty-line">No action hashes have been recorded yet.</div> : (bounty.transactions ?? []).slice().reverse().map((item) => <div className="trail-row" key={item.action}><span><small>{item.action}</small><code>{short(item.hash)}</code></span><a href={`${EXPLORER}/tx/${item.hash}`} target="_blank" rel="noreferrer" aria-label={`Open ${item.action} transaction`}><ExternalLink size={13} /></a></div>)}
        </section>

        {activity.length > 0 && <section className="panel activity-panel compact-activity"><div className="panel-heading"><div><h2>Current session</h2><p>{activity.length} wallet write{activity.length === 1 ? "" : "s"}</p></div></div>{activity.map((item) => <div className="activity-row" key={item.hash}><div className="activity-copy"><strong>{item.title}</strong><a href={`${EXPLORER}/tx/${item.hash}`} target="_blank" rel="noreferrer">{short(item.hash)} <ExternalLink size={12} /></a>{item.error && <small className="error-copy">{item.error}</small>}</div><span className={`status-tag ${stateTone(item.state)}`}>{item.state.replaceAll("_", " ")}</span></div>)}</section>}
      </aside>
    </div>

    {activity.map((item) => <SessionPoll key={item.hash} hash={item.hash} onState={onState} />)}
    <footer className="page-footer"><Link href="/"><ArrowLeft size={12} /> Back to queue</Link><span>GitHub fetch failure or evidence over 30 KB returns the bond.</span><span>Recorded proof is separate from this live case read.</span></footer>
  </main>;
}

function SessionPoll({ hash, onState }: { hash: string; onState: (hash: string, state: TxState, error?: string | null) => void }) {
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const response = await fetch(`/api/transactions/${hash}`, { cache: "no-store" });
        const view = await response.json() as TxView;
        if (!active || !response.ok) return;
        onState(hash, view.state, view.error);
        if (!["FINALIZED_SUCCESS", "FINALIZED_ERROR"].includes(view.state)) timer = setTimeout(poll, 5_000);
      } catch { if (active) timer = setTimeout(poll, 8_000); }
    };
    void poll();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [hash, onState]);
  return null;
}
