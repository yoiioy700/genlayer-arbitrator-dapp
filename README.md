# AI Arbitrator — On-Chain Arbitration Record & Dispute Adjudication on GenLayer

A decentralized, autonomous dispute **arbitration record** platform for freelance work, built on **GenLayer**.

When clients and freelancers face milestone disagreements, GenLayer AI validators independently evaluate the agreed job requirements against submitted deliverables and reach consensus on a recommended resolution via the **Equivalence Principle** (`gl.eq_principle.strict_eq`).

> **Scope & honest limitations (read first):**
> * This contract is an **arbitration oracle / record**, not a custodial escrow. It never receives, holds, locks, or transfers funds. The `amount` field is informational metadata recorded by the parties; actual settlement happens **off-chain, by the parties themselves**.
> * Verdicts are produced by LLM validators. Parties control the `requirements` and `deliverable` text fed to the model, so **prompt injection is a known structural limitation** — treat verdicts as advisory evidence, not ground truth.
> * A failed validator response falls back deterministically to `SPLIT` (50/50) rather than reverting.

---

## 🌟 Architecture & Key Invariants

1. **Deterministic State Partition:**
   Contract state (`TreeMap[str, DisputeCase]`) stores verified case metadata, agreed requirement briefs, deliverable proof, and final adjudication outcomes with native `u256` integer typing.
2. **Deterministic Equivalence Principle Consensus (`strict_eq`):**
   Non-deterministic natural-language reasoning is isolated in `gl.nondet.exec_prompt`. Validator committees evaluate deliverable fulfillment against the requirement brief and reach semantic consensus on fund allocation (`FREELANCER`, `CLIENT`, or `SPLIT`). To prevent validator rotation timeouts from subtle text variances, verdict normalization occurs before strict equivalence hashing.
3. **Storage Boundary Enforcement:**
   Storage data is strictly copied into local string primitives before entering non-deterministic closures, preventing GenVM sub-VM pickling warnings and memory sandbox violations.

---

## 🛡️ Security Invariants & Access Control

* **Invariant 1 (Collision Resistance):** `create_case` verifies `case_id not in self.cases` to prevent malicious overwrites of active or settled case records.
* **Invariant 1b (No Self-Dealing):** `create_case` rejects `freelancer == sender`, preventing a single actor from fabricating a two-party "AI-resolved" dispute record.
* **Invariant 2 (Deliverable Authorization):** `submit_deliverable` enforces caller verification (`sender == case.freelancer or sender == case.client`), preventing third-party deliverable tampering.
* **Invariant 3 (Adjudication Gating):** `adjudicate_dispute` restricts callers to registered contract parties (`sender == case.client or sender == case.freelancer`) and requires `status == "SUBMITTED"` to prevent premature adjudication on empty proofs.
* **Invariant 4 (Finite State Machine):** Cases transition strictly `CREATED -> SUBMITTED -> RESOLVED`. No retroactive mutations or double-adjudications are permitted once settled.

---

## 📜 Verified Deployments

| Network | Chain ID | Contract Address | Status | Explorer |
| :--- | :--- | :--- | :--- | :--- |
| **GenLayer Asimov Testnet** | 4221 | `0x498a595eE9F003F1b6cB585B322470a583F09684` | Finalized (`FINISHED_WITH_RETURN`) | [View on Asimov Explorer](https://explorer-asimov.genlayer.com/address/0x498a595eE9F003F1b6cB585B322470a583F09684) |

### On-Chain Transaction Proofs (v1.3.0):
* **Contract Deploy:** [`0x331bc289302f0ec70a95018a0ac5a590dbecbed8c080a414e88f09acc0e845d4`](https://explorer-asimov.genlayer.com/tx/0x331bc289302f0ec70a95018a0ac5a590dbecbed8c080a414e88f09acc0e845d4)
* **Create Case:** `0x97ed62c6eb94644e...` (case `case_v13_01`)
* **Submit Deliverable:** [`0x0beebebfa46eade57da98477a355d6a6757269ae457c0608887fefa8c5371b36`](https://explorer-asimov.genlayer.com/tx/0x0beebebfa46eade57da98477a355d6a6757269ae457c0608887fefa8c5371b36) -> `FINISHED_WITH_RETURN`
* **AI Consensus Adjudication (RESOLVED):** [`0x7ea4ea1e0b14a754647e4a2980b3e74efd4e8fc537cacfa6b8ee5aa938c1f175`](https://explorer-asimov.genlayer.com/tx/0x7ea4ea1e0b14a754647e4a2980b3e74efd4e8fc537cacfa6b8ee5aa938c1f175) -> `FINISHED_WITH_RETURN`, final state: `RESOLVED / FREELANCER / 0% client share`
* **Self-Dealing Guard:** a `create_case` call with `freelancer == sender` finalized with a failed execution and **no state change** (`selfdeal_v13` absent, `total_cases` unchanged) — Invariant 1b verified live on this contract.

---

## 💻 Running the Frontend

The dApp frontend is built with **Next.js 16 (Turbopack)** and directly uses `genlayer-js` to connect to GenLayer Asimov:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to record arbitration cases, submit deliverables, and trigger AI arbitrator adjudication.

---

## 🧪 Unit Tests

Tests run on [genlayer-test](https://pypi.org/project/genlayer-test/) direct mode (GenVM executed in-process, no simulator needed):

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python "genlayer-test>=0.29" pytest
.venv/bin/python -m pytest tests/ -q
```

Coverage: initial state, create/get, case-ID collision, self-dealing rejection, third-party submit/adjudicate rejection, premature adjudication rejection, full adjudication lifecycle with mocked LLM consensus (FREELANCER verdict + post-resolve immutability), and non-JSON LLM response falling back to `SPLIT`.
