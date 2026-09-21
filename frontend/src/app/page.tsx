"use client";

import { useState, useEffect } from "react";
import { createClient, chains } from "genlayer-js";

const CONTRACT_ADDRESS = "0xe822FA3A2b6aA657EddBEbbFF8dC1F9926695e36";
const EXPLORER_BASE = "https://explorer-asimov.genlayer.com";

interface OnChainCase {
  case_id: string;
  client: string;
  freelancer: string;
  amount: number;
  requirements: string;
  deliverable: string;
  status: string;
  verdict: string;
  client_share_pct: number;
  reason: string;
}

export default function Home() {
  const [account, setAccount] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"create" | "deliver" | "dispute" | "view">("create");
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [lastTxHash, setLastTxHash] = useState<string | null>(null);

  // Form states
  const [caseId, setCaseId] = useState("");
  const [freelancerAddr, setFreelancerAddr] = useState("");
  const [amountWei, setAmountWei] = useState("1");
  const [requirements, setRequirements] = useState("");
  const [deliverableText, setDeliverableText] = useState("");

  // Inspect state
  const [inspectId, setInspectId] = useState("case_escrow_01");
  const [inspectedCase, setInspectedCase] = useState<OnChainCase | null>(null);
  const [totalCases, setTotalCases] = useState<number | null>(null);

  // Initialize public client for reads
  const getPublicClient = () => {
    return createClient({ chain: chains.testnetAsimov });
  };

  // Connect wallet
  const connectWallet = async () => {
    if (typeof window !== "undefined" && (window as any).ethereum) {
      try {
        const accounts = await (window as any).ethereum.request({
          method: "eth_requestAccounts",
        });
        if (accounts && accounts.length > 0) {
          setAccount(accounts[0]);
        }
      } catch (err: any) {
        setStatusMessage(`Wallet connection failed: ${err.message}`);
      }
    } else {
      setStatusMessage("MetaMask or compatible Web3 wallet not detected.");
    }
  };

  // Fetch contract stats
  const fetchTotalCases = async () => {
    try {
      const client = getPublicClient();
      const count = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "get_total_cases",
        args: [],
      });
      setTotalCases(Number(count));
    } catch (e) {
      console.warn("Failed to fetch total cases:", e);
    }
  };

  useEffect(() => {
    fetchTotalCases();
  }, []);

  // 1. Create Case
  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !freelancerAddr || !requirements) {
      setStatusMessage("Please fill in all required fields.");
      return;
    }

    setIsProcessing(true);
    setStatusMessage("Submitting create_case transaction to GenLayer Asimov...");
    setLastTxHash(null);

    try {
      const client = createClient({
        chain: chains.testnetAsimov,
      });

      const tx = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "create_case",
        args: [caseId, freelancerAddr, BigInt(amountWei), requirements],
        value: 0n,
      });

      setLastTxHash(tx);
      setStatusMessage(`Transaction broadcasted: ${tx}. Waiting for consensus...`);

      const receipt = await client.waitForTransactionReceipt({ hash: tx });
      setStatusMessage(`Case "${caseId}" created successfully! Status: ${receipt.statusName || "ACCEPTED"}`);
      fetchTotalCases();
      setCaseId("");
      setFreelancerAddr("");
      setRequirements("");
    } catch (err: any) {
      setStatusMessage(`Transaction error: ${err.message || String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // 2. Submit Deliverable
  const handleSubmitDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !deliverableText) {
      setStatusMessage("Please specify Case ID and deliverable proof.");
      return;
    }

    setIsProcessing(true);
    setStatusMessage("Submitting deliverable on-chain...");
    setLastTxHash(null);

    try {
      const client = createClient({
        chain: chains.testnetAsimov,
      });

      const tx = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "submit_deliverable",
        args: [caseId, deliverableText],
        value: 0n,
      });

      setLastTxHash(tx);
      setStatusMessage(`Deliverable tx broadcasted: ${tx}. Waiting for block inclusion...`);
      await client.waitForTransactionReceipt({ hash: tx });
      setStatusMessage(`Deliverable for "${caseId}" recorded on GenLayer!`);
      setDeliverableText("");
    } catch (err: any) {
      setStatusMessage(`Error: ${err.message || String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // 3. Adjudicate Dispute via AI Consensus
  const handleAdjudicate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId) {
      setStatusMessage("Please specify Case ID to adjudicate.");
      return;
    }

    setIsProcessing(true);
    setStatusMessage("Triggering GenLayer Equivalence Principle consensus across AI validator committee...");
    setLastTxHash(null);

    try {
      const client = createClient({
        chain: chains.testnetAsimov,
      });

      const tx = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "adjudicate_dispute",
        args: [caseId],
        value: 0n,
      });

      setLastTxHash(tx);
      setStatusMessage(`Adjudication tx sent: ${tx}. AI Validators are voting...`);
      const receipt = await client.waitForTransactionReceipt({ hash: tx });
      setStatusMessage(`Adjudication completed! Consensus result: ${receipt.resultName || "AGREE"}`);
      
      // Auto inspect the case after resolution
      handleInspectCase(caseId);
    } catch (err: any) {
      setStatusMessage(`Adjudication failed: ${err.message || String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // 4. View Case on-chain
  const handleInspectCase = async (targetId?: string) => {
    const queryId = targetId || inspectId;
    if (!queryId) return;

    setStatusMessage(`Reading case "${queryId}" directly from GenLayer Asimov state...`);
    try {
      const client = getPublicClient();
      const res = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "get_case",
        args: [queryId],
      });
      setInspectedCase(res as unknown as OnChainCase);
      setStatusMessage(`Case "${queryId}" loaded from on-chain storage.`);
    } catch (err: any) {
      setInspectedCase(null);
      setStatusMessage(`Case not found or not yet registered: ${err.message || String(err)}`);
    }
  };

  return (
    <div className="container" style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Top Navbar */}
      <nav className="navbar" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2.5rem" }}>
        <div className="logo" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: 22, fontWeight: 700 }}>⚖️ GenLayer Escrow</span>
          <span className="logo-badge" style={{ fontSize: 11, background: "rgba(6, 182, 212, 0.15)", color: "var(--accent-cyan)", padding: "3px 8px", borderRadius: 6, border: "1px solid rgba(6, 182, 212, 0.3)" }}>
            Asimov Testnet
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <a
            href={`${EXPLORER_BASE}/address/${CONTRACT_ADDRESS}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: 12, color: "var(--text-secondary)", textDecoration: "none" }}
          >
            Contract: {CONTRACT_ADDRESS.slice(0, 6)}...{CONTRACT_ADDRESS.slice(-4)} ↗
          </a>
          {account ? (
            <span style={{ fontSize: 13, background: "rgba(255, 255, 255, 0.05)", padding: "6px 14px", borderRadius: 8, border: "1px solid var(--border-glass)" }}>
              {account.slice(0, 6)}...{account.slice(-4)}
            </span>
          ) : (
            <button
              onClick={connectWallet}
              style={{ background: "var(--gradient-main)", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 8, fontWeight: 600, cursor: "pointer", fontSize: 13 }}
            >
              Connect Wallet
            </button>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <header style={{ textAlign: "center", marginBottom: "3rem" }}>
        <h1 style={{ fontSize: "2.5rem", fontWeight: 800, marginBottom: "0.8rem", letterSpacing: "-0.03em" }}>
          Decentralized Freelance Escrow & <span style={{ background: "var(--gradient-main)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AI Dispute Resolution</span>
        </h1>
        <p style={{ color: "var(--text-secondary)", maxWidth: 680, margin: "0 auto", fontSize: "1.05rem", lineHeight: 1.6 }}>
          Automated milestone fund release backed by real GenLayer Intelligent Contracts. Non-deterministic evaluation is judged by validator LLMs reaching consensus under the Equivalence Principle.
        </p>
        {totalCases !== null && (
          <div style={{ marginTop: "1rem", fontSize: 13, color: "var(--accent-emerald)" }}>
            ● Verified On-Chain: <strong>{totalCases}</strong> total escrow cases registered
          </div>
        )}
      </header>

      {/* Tabs */}
      <div style={{ display: "flex", justifyContent: "center", gap: 10, marginBottom: "2rem" }}>
        {(["create", "deliver", "dispute", "view"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "10px 20px",
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === tab ? "1px solid var(--accent-cyan)" : "1px solid var(--border-glass)",
              background: activeTab === tab ? "rgba(6, 182, 212, 0.12)" : "rgba(255, 255, 255, 0.02)",
              color: activeTab === tab ? "var(--accent-cyan)" : "var(--text-secondary)",
              transition: "all 0.2s ease"
            }}
          >
            {tab === "create" && "1. Create Escrow"}
            {tab === "deliver" && "2. Submit Deliverable"}
            {tab === "dispute" && "3. AI Adjudication"}
            {tab === "view" && "4. Inspect On-Chain"}
          </button>
        ))}
      </div>

      {/* Interactive Container */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-glass)", borderRadius: 18, padding: "2rem", boxShadow: "var(--shadow-card)", marginBottom: "2rem" }}>
        {/* Tab 1: Create Case */}
        {activeTab === "create" && (
          <form onSubmit={handleCreateCase}>
            <h3 style={{ fontSize: "1.3rem", marginBottom: "1rem" }}>Create New Escrow Case</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Case ID / Slug</label>
                <input
                  type="text"
                  placeholder="e.g. project_frontend_01"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Freelancer Address</label>
                <input
                  type="text"
                  placeholder="0x..."
                  value={freelancerAddr}
                  onChange={(e) => setFreelancerAddr(e.target.value)}
                  style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
                  required
                />
              </div>
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Escrow Amount (Wei / Tokens)</label>
              <input
                type="number"
                value={amountWei}
                onChange={(e) => setAmountWei(e.target.value)}
                style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
                required
              />
            </div>
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Agreed Requirements & Success Criteria</label>
              <textarea
                rows={4}
                placeholder="Describe milestone deliverables, technical spec, and criteria for fund release..."
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff", resize: "vertical" }}
                required
              />
            </div>
            <button
              type="submit"
              disabled={isProcessing}
              style={{ background: "var(--gradient-main)", color: "#fff", border: "none", padding: "12px 24px", borderRadius: 8, fontWeight: 700, cursor: isProcessing ? "not-allowed" : "pointer" }}
            >
              {isProcessing ? "Processing On-Chain..." : "Lock Escrow on GenLayer"}
            </button>
          </form>
        )}

        {/* Tab 2: Submit Deliverable */}
        {activeTab === "deliver" && (
          <form onSubmit={handleSubmitDeliverable}>
            <h3 style={{ fontSize: "1.3rem", marginBottom: "1rem" }}>Submit Work Deliverable</h3>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Case ID</label>
              <input
                type="text"
                placeholder="case_escrow_01"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
                required
              />
            </div>
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Submitted Deliverable (Repo link, preview URL, or text)</label>
              <textarea
                rows={4}
                placeholder="Paste github repository link, testnet contract address, or summary of delivered milestones..."
                value={deliverableText}
                onChange={(e) => setDeliverableText(e.target.value)}
                style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
                required
              />
            </div>
            <button
              type="submit"
              disabled={isProcessing}
              style={{ background: "var(--accent-cyan)", color: "#000", border: "none", padding: "12px 24px", borderRadius: 8, fontWeight: 700, cursor: isProcessing ? "not-allowed" : "pointer" }}
            >
              {isProcessing ? "Submitting..." : "Submit Deliverable Proof"}
            </button>
          </form>
        )}

        {/* Tab 3: Dispute & Adjudicate */}
        {activeTab === "dispute" && (
          <form onSubmit={handleAdjudicate}>
            <h3 style={{ fontSize: "1.3rem", marginBottom: "1rem" }}>AI Consensus Adjudication</h3>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
              Triggers the GenLayer Equivalence Principle. Multi-validator LLM instances review the requirement brief against the submitted deliverable and reach semantic consensus on fund split.
            </p>
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Target Case ID</label>
              <input
                type="text"
                placeholder="case_escrow_01"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                style={{ width: "100%", padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
                required
              />
            </div>
            <button
              type="submit"
              disabled={isProcessing}
              style={{ background: "linear-gradient(135deg, #f43f5e, #8b5cf6)", color: "#fff", border: "none", padding: "12px 24px", borderRadius: 8, fontWeight: 700, cursor: isProcessing ? "not-allowed" : "pointer" }}
            >
              {isProcessing ? "Arbitrators Deliberating..." : "Execute AI Arbitrator Consensus"}
            </button>
          </form>
        )}

        {/* Tab 4: Inspect State */}
        {activeTab === "view" && (
          <div>
            <h3 style={{ fontSize: "1.3rem", marginBottom: "1rem" }}>Inspect On-Chain Case State</h3>
            <div style={{ display: "flex", gap: 10, marginBottom: "1.5rem" }}>
              <input
                type="text"
                placeholder="Case ID to inspect"
                value={inspectId}
                onChange={(e) => setInspectId(e.target.value)}
                style={{ flex: 1, padding: 12, borderRadius: 8, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-glass)", color: "#fff" }}
              />
              <button
                type="button"
                onClick={() => handleInspectCase()}
                style={{ background: "rgba(255,255,255,0.1)", color: "#fff", border: "1px solid var(--border-glass)", padding: "12px 20px", borderRadius: 8, fontWeight: 600, cursor: "pointer" }}
              >
                Read State
              </button>
            </div>

            {inspectedCase && (
              <div style={{ background: "rgba(0,0,0,0.4)", borderRadius: 12, padding: "1.5rem", border: "1px solid var(--border-glass)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
                  <span style={{ fontSize: 18, fontWeight: 700 }}>Case: {inspectedCase.case_id}</span>
                  <span style={{
                    padding: "4px 10px",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 700,
                    background: inspectedCase.status === "RESOLVED" ? "rgba(16, 185, 129, 0.2)" : "rgba(245, 158, 11, 0.2)",
                    color: inspectedCase.status === "RESOLVED" ? "var(--accent-emerald)" : "var(--accent-amber)"
                  }}>
                    {inspectedCase.status}
                  </span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: 13, marginBottom: "1rem" }}>
                  <div><strong>Client:</strong> {inspectedCase.client}</div>
                  <div><strong>Freelancer:</strong> {inspectedCase.freelancer}</div>
                  <div><strong>Amount (Wei):</strong> {inspectedCase.amount}</div>
                  <div><strong>AI Verdict:</strong> {inspectedCase.verdict} ({inspectedCase.client_share_pct}% refund to Client)</div>
                </div>
                <div style={{ fontSize: 13, marginBottom: "0.5rem" }}><strong>Requirements:</strong> {inspectedCase.requirements}</div>
                <div style={{ fontSize: 13, marginBottom: "0.5rem" }}><strong>Deliverable:</strong> {inspectedCase.deliverable || "(Pending)"}</div>
                {inspectedCase.reason && (
                  <div style={{ marginTop: "1rem", padding: "10px", borderRadius: 6, background: "rgba(6, 182, 212, 0.08)", border: "1px solid rgba(6, 182, 212, 0.2)", fontSize: 13 }}>
                    <strong>Consensus Reasoning:</strong> {inspectedCase.reason}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Live Status Toast / Bar */}
        {statusMessage && (
          <div style={{ marginTop: "1.5rem", padding: "12px 16px", borderRadius: 8, background: "rgba(255,255,255,0.03)", border: "1px solid var(--border-glass)", fontSize: 13, color: "var(--accent-cyan)" }}>
            {statusMessage}
            {lastTxHash && (
              <div style={{ marginTop: 6 }}>
                <a href={`${EXPLORER_BASE}/tx/${lastTxHash}`} target="_blank" rel="noopener noreferrer" style={{ color: "#fff", textDecoration: "underline" }}>
                  View Transaction on GenLayer Explorer ↗
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Architecture Footer */}
      <footer style={{ textAlign: "center", fontSize: 12, color: "var(--text-muted)", marginTop: "3rem" }}>
        Powered by GenLayer GenVM · Equivalence Principle Validator Consensus · CPython 3.13 WebAssembly Sandbox
      </footer>
    </div>
  );
}
