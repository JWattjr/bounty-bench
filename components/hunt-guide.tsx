"use client";

import { Check, Copy, Droplets, ExternalLink, ShieldCheck, TerminalSquare } from "lucide-react";
import { useState } from "react";
import { fundTestAccount, preflightClaim, type Preflight } from "@/lib/github";

export default function HuntGuide({ repo, base, account, bondWei, headSha, setHeadSha }: {
  repo: string; base: string; account: string; bondWei: string; headSha: string; setHeadSha: (value: string) => void;
}) {
  const [copied, setCopied] = useState("");
  const [check, setCheck] = useState<Preflight | null>(null);
  const [checking, setChecking] = useState(false);
  const [funding, setFunding] = useState("");
  const name = repo.split("/")[1] ?? repo;
  const trailer = account ? `Bounty-Claimant: ${account}` : "Bounty-Claimant: <connect your wallet to see this line>";
  const commands = [
    `git clone https://github.com/${repo}.git && cd ${name}`,
    `git checkout -b my-fix ${base}`,
    "# make the change and add a test, then:",
    `git commit -am "Fix the bug" -m "${trailer}"`,
    "git push origin my-fix   # push to your public fork",
  ].join("\n");

  async function copy(label: string, text: string) {
    try { await navigator.clipboard.writeText(text); setCopied(label); setTimeout(() => setCopied(""), 1500); } catch { /* clipboard unavailable */ }
  }
  async function run() {
    if (!account) { setCheck({ ok: false, title: "Connect your wallet first", detail: "The claimant line depends on your wallet address." }); return; }
    setChecking(true); setCheck(await preflightClaim(repo, base, headSha.trim(), account)); setChecking(false);
  }
  async function fund() {
    if (!account) { setFunding("Connect your wallet first."); return; }
    setFunding("Requesting test GEN…");
    try { await fundTestAccount(account); setFunding(`Done. Your wallet can now post the ${bondWei} wei claim bond.`); }
    catch (error) { setFunding(error instanceof Error ? error.message : "The faucet is unavailable."); }
  }

  return <section className="panel hunt-panel">
    <div className="panel-heading"><div><h2>Hunt this bounty</h2><p>Fix it, prove it is yours, claim the reward in four steps.</p></div><span className="action-mark"><TerminalSquare size={15} /></span></div>
    <ol className="hunt-steps">
      <li><strong>Get test GEN.</strong> A claim needs a {bondWei} wei bond. <button className="text-button" onClick={() => void fund()}><Droplets size={12} /> Fund my wallet</button>{funding && <small className="hunt-note">{funding}</small>}</li>
      <li><strong>Fork and branch from the pinned base.</strong> Judging compares your head to <code>{base.slice(0, 10)}</code>. <a className="text-link" href={`https://github.com/${repo}/fork`} target="_blank" rel="noreferrer">Fork {repo} <ExternalLink size={11} /></a></li>
      <li><strong>Commit the fix and a test, with your claimant line.</strong>
        <pre className="hunt-code">{commands}</pre>
        <div className="hunt-actions"><button className="text-button" onClick={() => void copy("commands", commands)}>{copied === "commands" ? <Check size={12} /> : <Copy size={12} />} Copy commands</button><button className="text-button" onClick={() => void copy("line", trailer)} disabled={!account}>{copied === "line" ? <Check size={12} /> : <Copy size={12} />} Copy claimant line</button></div>
      </li>
      <li><strong>Check your commit, then claim.</strong> Paste your head SHA in the field below. <button className="text-button" onClick={() => void run()} disabled={checking || headSha.trim().length === 0}><ShieldCheck size={12} /> {checking ? "Checking…" : "Check my commit"}</button>
        {check && <p className={`hunt-result ${check.ok ? "tone-good" : "tone-bad"}`}><strong>{check.title}.</strong> {check.detail}</p>}
      </li>
    </ol>
    <p className="form-note"><ShieldCheck size={13} /> The check runs in your browser against GitHub. The on-chain identity check is the one that counts.</p>
  </section>;
}
