"use client";

import { ArrowLeft, ArrowUpRight, ExternalLink, ScanSearch, ShieldCheck, Wallet } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Proof, ScoutDraft, ScoutSnapshot } from "@/lib/domain";
import { short } from "@/lib/domain";
import { walletAccount, write } from "@/lib/wallet";

function parseIssue(value: string) {
  const url = value.trim().match(/^https:\/\/github\.com\/([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)\/issues\/(\d+)\/?$/);
  return url ? { repo: url[1], number: Number(url[2]) } : null;
}

export default function Scout({ proof }: { proof: Proof }) {
  const scoutAddress = proof.contracts.IssueScout?.address ?? "";
  const [snapshot, setSnapshot] = useState<ScoutSnapshot | null>(null);
  const [loadError, setLoadError] = useState("");
  const [issue, setIssue] = useState("https://github.com/JWattjr/bounty-bench-fixtures/issues/2");
  const [account, setAccount] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [submitted, setSubmitted] = useState("");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/scout", { cache: "no-store" });
      const value = await response.json() as ScoutSnapshot;
      setSnapshot(value);
      setLoadError(value.error ?? "");
    } catch (error) { setLoadError(error instanceof Error ? error.message : "StudioNet read failed."); }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(timer);
  }, [refresh]);

  const recorded = useMemo(() => Object.values(proof.scout?.records ?? {}).reverse(), [proof.scout]);
  const drafts: ScoutDraft[] = snapshot && snapshot.drafts.length ? snapshot.drafts : recorded;
  const showingRecorded = !(snapshot && snapshot.drafts.length);

  async function connect() {
    setActionError("");
    try { setAccount((await walletAccount()).account); }
    catch (error) { setActionError(error instanceof Error ? error.message : "Wallet connection failed."); }
  }
  async function scout(event: React.FormEvent) {
    event.preventDefault();
    const parsed = parseIssue(issue);
    if (!parsed) { setActionError("Paste a public GitHub issue URL like https://github.com/owner/repo/issues/12."); return; }
    setBusy(true); setActionError(""); setSubmitted("");
    try {
      const hash = await write(scoutAddress, "draft", [parsed.repo, parsed.number]);
      setSubmitted(hash);
      if (!account) setAccount((await walletAccount()).account);
    } catch (error) { setActionError(error instanceof Error ? error.message : "Scouting failed."); }
    finally { setBusy(false); }
  }

  return <main className="shell">
    <header className="topbar">
      <Link className="brand-lockup" href="/"><span className="brand-mark">BB</span><span>Bounty Bench</span></Link>
      <nav className="topnav"><Link href="/">Board</Link><a className="nav-active" href="#drafts">Scout an issue</a></nav>
      <div className="topbar-right"><span className="network-chip"><i /> StudioNet <b>61999</b></span><button className="button button-quiet" onClick={connect}><Wallet size={14} /> {account ? short(account) : "Connect wallet"}</button></div>
    </header>

    <div className="breadcrumb"><Link href="/"><ArrowLeft size={14} /> Bounty board</Link><span>/</span><span>Scout an issue</span></div>
    <section className="case-heading">
      <div><h1>Turn a GitHub issue into a bounty</h1><p>Paste any open public issue. Validators read it, draft one to four criteria a code diff can prove, and reject drafts that name anything the issue does not say. You review the draft, then post it with a reward.</p></div>
      <div className="case-reward"><span>DRAFTS SHOWN</span><strong>{drafts.length}<small> recent</small></strong><span>IssueScout contract</span></div>
    </section>

    <div className="detail-grid">
      <div className="detail-main" id="drafts">
        <section className="panel">
          <div className="panel-heading"><div><h2>Scouted issues</h2><p>{showingRecorded ? "Recorded proof drafts" : "Latest finalized drafts"} · criteria are frozen at draft time</p></div><span className="action-mark"><ScanSearch size={15} /></span></div>
          {loadError && <div className="inline-error"><strong>{showingRecorded ? "Live read unavailable, showing recorded proof." : "Showing last good live read."}</strong><span>{loadError}</span><button onClick={() => void refresh()}>Retry</button></div>}
          {drafts.length === 0 && <div className="empty-line">No drafts yet. Scout the first issue.</div>}
          {drafts.map((draft) => {
            const params = new URLSearchParams({ repo: draft.repo, title: `Fix: ${draft.issue_title}`.slice(0, 140) });
            draft.criteria.forEach((criterion) => params.append("criterion", criterion));
            return <article className="verdict-row" key={draft.id}>
              <div className="verdict-top"><span className="criterion-index">{draft.id.replace("draft-", "")}</span><strong>{draft.issue_title || `${draft.repo}#${draft.issue_number}`}</strong><span className={`status-tag ${draft.status === "DRAFTED" ? "tone-good" : "tone-bad"}`}>{draft.status}</span></div>
              <div className="evidence-meta"><span><small>ISSUE</small><a className="text-link" href={`https://github.com/${draft.repo}/issues/${draft.issue_number}`} target="_blank" rel="noreferrer">{draft.repo}#{draft.issue_number} <ExternalLink size={12} /></a></span><span><small>ISSUE DIGEST</small><code>{draft.issue_digest ? draft.issue_digest.slice(0, 16) : "none"}</code></span></div>
              {draft.status === "DRAFTED" ? <div className="criteria-list">{draft.criteria.map((criterion, index) => <div className="criterion-row" key={criterion}><span className="criterion-index">{String(index + 1).padStart(2, "0")}</span><div className="criterion-body"><strong>{criterion}</strong></div></div>)}</div> : <p className="verdict-reason">{draft.reason}</p>}
              {draft.status === "DRAFTED" && <Link className="button button-primary" href={`/?${params.toString()}#post`}>Post this as a bounty <ArrowUpRight size={13} /></Link>}
            </article>;
          })}
        </section>
      </div>

      <aside className="detail-side">
        <section className="panel action-panel">
          <div className="panel-heading"><div><h2>Scout an issue</h2><p>One write call. No money moves.</p></div><span className="action-mark"><Wallet size={15} /></span></div>
          <form className="create-form" onSubmit={scout}>
            <label>Public issue URL<input className="mono-input" value={issue} onChange={(event) => setIssue(event.target.value)} placeholder="https://github.com/owner/repo/issues/12" /></label>
            {actionError && <p className="form-error">{actionError}</p>}
            {submitted && <p className="form-note"><ShieldCheck size={13} /> Submitted. Validators need a few minutes; the draft appears on the left when it finalizes. <a className="text-link" href={`https://explorer-studio.genlayer.com/tx/${submitted}`} target="_blank" rel="noreferrer">Transaction {short(submitted)}</a></p>}
            <button className="button button-primary full-width" disabled={busy || !scoutAddress}>{busy ? "Waiting for wallet…" : "Draft criteria with validators"}</button>
          </form>
          <p className="form-note"><ShieldCheck size={13} /> Validators re-read the issue and check every draft in code: allowed shapes, one behavior criterion, and only identifiers the issue actually contains. Vague issues come back UNACTIONABLE.</p>
        </section>
      </aside>
    </div>
  </main>;
}
