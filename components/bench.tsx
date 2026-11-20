"use client";

import { Activity, ArrowDownRight, ArrowUpRight, ExternalLink, GitBranch, ShieldCheck, Wallet } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { short, type Bounty, type Proof, type Snapshot, type TxState } from "@/lib/domain";
import { walletAccount, write } from "@/lib/wallet";

const EXPLORER = "https://explorer-studio.genlayer.com";

function timeLabel(seconds?: number) {
  if (!seconds) return "—";
  const delta = seconds - Math.floor(Date.now() / 1000);
  if (delta <= 0) return "Grace period";
  const hours = Math.floor(delta / 3600);
  const minutes = Math.floor((delta % 3600) / 60);
  return hours > 24 ? `${Math.floor(hours / 24)}d ${hours % 24}h` : `${hours}h ${minutes}m`;
}

function stateTone(status: string) {
  if (["OPEN", "WON", "CLOSED", "REJECTED_REFUNDED", "FINALIZED_SUCCESS", "MET"].includes(status)) return "tone-good";
  if (["COMPILING", "PENDING", "JUDGING", "AWARD_PENDING", "WAITING_FOR_DEADLINE_GRACE", "ACCEPTED"].includes(status)) return "tone-wait";
  if (["SPEC_REJECTED", "FAILED", "IDENTITY_MISMATCH", "FINALIZED_ERROR", "NOT_MET"].includes(status)) return "tone-bad";
  return "tone-neutral";
}

function TxFeed({ hash, title, onState }: { hash: string; title: string; onState: (hash: string, state: TxState, error?: string | null) => void }) {
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const response = await fetch(`/api/transactions/${hash}`, { cache: "no-store" });
        const view = await response.json();
        if (!active || !response.ok) return;
        onState(hash, view.state, view.error);
        if (!["FINALIZED_SUCCESS", "FINALIZED_ERROR"].includes(view.state)) timer = setTimeout(poll, 5_000);
      } catch {
        if (active) timer = setTimeout(poll, 8_000);
      }
    };
    void poll();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [hash, onState]);
  return <span className="tx-feed-title">{title}</span>;
}

function TxStateLine({ hash, title, state, error, onState }: { hash: string; title: string; state: TxState; error?: string | null; onState: (hash: string, state: TxState, error?: string | null) => void }) {
  return <div className="activity-row">
    <div className="activity-copy"><TxFeed hash={hash} title={title} onState={onState} /><a href={`${EXPLORER}/tx/${hash}`} target="_blank" rel="noreferrer">{short(hash)} <ExternalLink size={12} /></a>{error && <small className="error-copy">{error}</small>}</div>
    <span className={`status-tag ${stateTone(state)}`}>{state.replaceAll("_", " ")}</span>
  </div>;
}

export default function Bench({ proof }: { proof: Proof }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadError, setLoadError] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [account, setAccount] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [activity, setActivity] = useState<{ hash: string; title: string; state: TxState; error?: string | null }[]>([]);
  const [form, setForm] = useState({ repo: "owner/repository", base: "", title: "", criteria: "", reward: "50", bond: "5", hours: "24" });
  const board = proof.contracts.BountyBoard?.address ?? "";

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/live", { cache: "no-store" });
      const value = await response.json() as Snapshot;
      setSnapshot(value);
      setLoadError(value.error ?? "");
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "The StudioNet read failed.");
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const repo = params.get("repo");
    const criteria = params.getAll("criterion");
    if (repo && criteria.length) {
      setForm((current) => ({ ...current, repo, title: params.get("title") ?? current.title, criteria: criteria.join("\n"), reward: "10", bond: "1", hours: "504" }));
      void fetch(`https://api.github.com/repos/${repo}/commits/HEAD`, { headers: { Accept: "application/vnd.github+json" } })
        .then((response) => (response.ok ? response.json() : null))
        .then((data: { sha?: string } | null) => { if (data?.sha) setForm((current) => ({ ...current, base: data.sha ?? "" })); })
        .catch(() => undefined);
      setTimeout(() => document.getElementById("post")?.scrollIntoView(), 300);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(timer);
  }, [refresh]);

  const bounties = snapshot?.bounties ?? [];
  const visible = useMemo(() => filter === "ALL" ? bounties : bounties.filter((item) => filter === "OPEN" ? item.status === "OPEN" : item.status !== "OPEN"), [bounties, filter]);
  const onState = useCallback((hash: string, state: TxState, error?: string | null) => {
    setActivity((items) => items.map((item) => item.hash === hash ? { ...item, state, error } : item));
  }, []);

  async function connect() {
    setActionError("");
    try { const result = await walletAccount(); setAccount(result.account); }
    catch (error) { setActionError(error instanceof Error ? error.message : "Wallet connection failed."); }
  }

  async function createBounty(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionError("");
    const criteria = form.criteria.split("\n").map((line) => line.trim()).filter(Boolean);
    if (!board || criteria.length < 1 || criteria.length > 4 || !/^[0-9a-f]{40}$/i.test(form.base)) {
      setActionError("Enter a 40-character base SHA and one to four criteria, one per line."); return;
    }
    setBusy(true);
    try {
      const hash = await write(board, "create_bounty", [form.repo.trim(), form.base.trim(), form.title.trim(), JSON.stringify(criteria), Math.floor(Date.now() / 1000) + Number(form.hours) * 3600, Number(form.bond)], BigInt(form.reward));
      setActivity((items) => [{ hash, title: "Create bounty", state: "SUBMITTED" }, ...items]);
      setAccount((await walletAccount()).account);
      setTimeout(() => void refresh(), 5_000);
    } catch (error) { setActionError(error instanceof Error ? error.message : "Bounty submission failed."); }
    finally { setBusy(false); }
  }

  return <main className="shell">
    <header className="topbar">
      <Link className="brand-lockup" href="/"><span className="brand-mark">BB</span><span>Bounty Bench</span></Link>
      <nav className="topnav"><a className="nav-active" href="#board">Board</a><Link href="/scout">Scout an issue</Link><a href="#proof">Release proof</a></nav>
      <div className="topbar-right"><span className="network-chip"><i /> StudioNet <b>61999</b></span><span className="read-state"><span className="pulse-dot" /> {snapshot ? "Live read" : "Connecting"}</span><button className="button button-quiet" onClick={connect}><Wallet size={14} /> {account ? short(account) : "Connect wallet"}</button></div>
    </header>

    <section className="intro-row">
      <div><p className="intro-line">Open code bounty protocol <span>/</span> Public review queue</p><h1>Pay on the diff.</h1><p className="intro-copy">Code bounties that pay on the diff, not on the maintainer’s mood.</p></div>
      <div className="intro-meta"><div><span>NETWORK</span><strong>GenLayer StudioNet</strong></div><div><span>READ SOURCE</span><strong>{snapshot ? "Latest finalized state" : "Waiting for RPC"}</strong></div><div><span>LAST READ</span><strong>{snapshot ? new Date(snapshot.readAt).toLocaleTimeString() : "—"}</strong></div></div>
    </section>

    <div className="workbench-grid" id="board">
      <section className="panel ledger-panel">
        <div className="panel-heading"><div><h2>Bounty queue</h2><p>Frozen criteria, ordered claims, finalized outcomes.</p></div><button className="icon-button" aria-label="Refresh board" onClick={() => void refresh()}><Activity size={16} /></button></div>
        <div className="filter-row">{["ALL", "OPEN", "CLOSED"].map((value) => <button key={value} className={filter === value ? "filter-active" : ""} onClick={() => setFilter(value)}>{value === "ALL" ? "All bounties" : value === "OPEN" ? "Open" : "Resolved"}<span>{value === "ALL" ? bounties.length : bounties.filter((item) => value === "OPEN" ? item.status === "OPEN" : item.status !== "OPEN").length}</span></button>)}</div>
        {loadError && <div className="inline-error"><strong>{snapshot?.stale && snapshot.bounties.length ? "Showing last good live read." : "Live read unavailable, showing recorded proof."}</strong><span>{loadError}</span><button onClick={() => void refresh()}>Retry</button></div>}
        {!snapshot && !loadError && <div className="empty-line">Reading finalized StudioNet state…</div>}
        {snapshot && visible.length === 0 && !loadError && <div className="empty-ledger"><GitBranch size={20} /><strong>No bounties in this view.</strong><span>Create the first one with a concrete diff-observable criterion.</span></div>}
        {visible.length > 0 && <div className="ledger-table">
          <div className="ledger-head"><span>BOUNTY / REPOSITORY</span><span>REWARD</span><span>QUEUE</span><span>DEADLINE</span><span>STATE</span></div>
          {visible.map((bounty, index) => <Link key={bounty.id} className="ledger-row" href={`/bounty/${encodeURIComponent(bounty.id)}`}>
            <span className="ledger-title"><span className="serial">{String(index + 1).padStart(2, "0")}</span><span><strong>{bounty.title}</strong><small>{bounty.repo} <span>·</span> {short(bounty.base_sha, 7, 5)}</small></span></span>
            <span className="mono amount">{bounty.reward_wei} <small>wei</small></span><span className="queue-count">{String(bounty.queue_length).padStart(2, "0")} <small>claims</small></span><span className="deadline-copy">{timeLabel(bounty.deadline)}</span><span className={`status-tag ${stateTone(bounty.status)}`}>{bounty.status.replaceAll("_", " ")}</span><ArrowUpRight className="row-arrow" size={15} />
          </Link>)}
        </div>}
        <div className="panel-foot"><span>{snapshot ? `${bounties.length} on-chain records returned` : "RPC snapshot is not a cached proof"}</span><span>Refreshes every 30 seconds</span></div>
      </section>

      <aside className="side-stack">
        <section className="panel create-panel" id="post">
          <div className="panel-heading"><div><h2>Post a bounty</h2><p>One payable call freezes the reward and criteria.</p></div><span className="action-mark"><ArrowDownRight size={15} /></span></div>
          <form className="create-form" onSubmit={createBounty}>
            <label>GitHub repository<input value={form.repo} onChange={(event) => setForm({ ...form, repo: event.target.value })} placeholder="owner/repository" /></label>
            <label>Base commit SHA<input className="mono-input" value={form.base} onChange={(event) => setForm({ ...form, base: event.target.value })} placeholder="40 hexadecimal characters" /></label>
            <label>Bounty title<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Describe the code change" /></label>
            <label>Acceptance criteria <small>One per line · up to four</small><textarea value={form.criteria} onChange={(event) => setForm({ ...form, criteria: event.target.value })} placeholder={'changes `function_name` so that it ...\nadds a test that exercises `function_name`'} rows={3} /></label>
            <div className="field-grid"><label>Reward <small>wei</small><input inputMode="numeric" value={form.reward} onChange={(event) => setForm({ ...form, reward: event.target.value })} /></label><label>Claim bond <small>wei</small><input inputMode="numeric" value={form.bond} onChange={(event) => setForm({ ...form, bond: event.target.value })} /></label><label>Deadline <small>hours</small><input inputMode="numeric" value={form.hours} onChange={(event) => setForm({ ...form, hours: event.target.value })} /></label></div>
            {actionError && <p className="form-error">{actionError}</p>}
            <button className="button button-primary full-width" disabled={busy || !board}>{busy ? "Waiting for wallet…" : "Review and publish"}</button>
            <p className="form-note"><ShieldCheck size={13} /> Invalid or rejected specs keep a refundable state.</p>
          </form>
        </section>

        <section className="panel proof-panel" id="proof">
          <div className="panel-heading"><div><h2>Recorded release proof</h2><p>Manifest snapshot · separate from live reads.</p></div><span className="proof-seal"><ShieldCheck size={15} /></span></div>
          <div className="proof-contracts">{Object.entries(proof.contracts).map(([name, item]) => <a key={name} href={`${EXPLORER}/address/${item.address}`} target="_blank" rel="noreferrer"><span><small>{name}</small><code>{short(item.address)}</code></span><ExternalLink size={13} /></a>)}</div>
          <div className="proof-summary"><span>Release state</span><strong className={stateTone(proof.releaseStatus)}>{proof.releaseStatus.replaceAll("_", " ")}</strong></div>
          <div className="proof-summary"><span>Recorded transactions</span><strong>{Object.keys(proof.transactions).length}</strong></div>
          <a className="text-link" href="/api/proof" target="_blank" rel="noreferrer">Open proof manifest <ExternalLink size={12} /></a>
        </section>
      </aside>
    </div>

    <section className="panel activity-panel">
      <div className="panel-heading"><div><h2>Wallet activity</h2><p>Transaction state is read from StudioNet after each submission.</p></div><span className="status-tag tone-neutral">{activity.length} local</span></div>
      {activity.length === 0 ? <div className="empty-line">No wallet writes in this session. You can inspect the board without connecting.</div> : activity.map((item) => <TxStateLine key={item.hash} {...item} onState={onState} />)}
    </section>

    <footer className="page-footer"><span>Bounty Bench <span>·</span> StudioNet</span><span>GitHub availability and the 30 KB evidence cap affect claim outcomes.</span><a href="https://github.com/JWattjr/bounty-bench-fixtures" target="_blank" rel="noreferrer">Fixture source <ExternalLink size={12} /></a></footer>
  </main>;
}
