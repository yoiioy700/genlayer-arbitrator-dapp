# AI Arbitrator — On-Chain Arbitration Record & Dispute Adjudication on GenLayer

A decentralized, autonomous dispute **arbitration record** platform for freelance work, built on **GenLayer**.

When clients and freelancers face milestone disagreements, the contract itself **fetches and hash-verifies the committed deliverable artifact**, then GenLayer AI validators independently evaluate the agreed job requirements against the verified evidence and reach consensus on a recommended resolution via the **Equivalence Principle** (`gl.eq_principle.strict_eq`).

> **Scope & honest limitations (read first):**
> * This contract is an **arbitration oracle / record**, not a custodial escrow. It never receives, holds, locks, or transfers funds. The `amount` field is informational metadata recorded by the parties; actual settlement happens **off-chain, by the parties themselves**.
> * **v1.4 evidence model:** at submission time the freelancer commits an `evidence_url` (https, static/raw artifact) plus its **keccak256 digest**. During adjudication each validator independently fetches the URL (`gl.nondet.web.get`), recomputes keccak256, and the verdict is **gated**: a full `FREELANCER` award requires `VERIFIED` evidence integrity — tampered (`HASH_MISMATCH`) or unreachable evidence cannot win a full award.
> * Verdicts are produced by LLM validators. Parties still control the `requirements` and `deliverable` text fed to the model, so **prompt injection in the prose fields remains a known structural limitation** — treat verdicts as advisory evidence, not ground truth.
> * A failed validator response falls back deterministically to `SPLIT` (50/50) rather than reverting.

---

## 🌟 Architecture & Key Invariants

1. **Deterministic State Partition:**
   Contract state (`TreeMap[str, DisputeCase]`) stores verified case metadata, agreed requirement briefs, deliverable claims, evidence commitments (`evidence_url` + `evidence_hash`), the retrieval result (`evidence_status`), and final adjudication outcomes with native `u256` integer typing.
2. **Contract-Side Evidence Retrieval & Validation (v1.4):**
   `submit_deliverable` requires an `https://` artifact URL and its `keccak256` commitment. Inside the non-deterministic block, every validator re-fetches the artifact with `gl.nondet.web.get`, recomputes `keccak256(body)` (GenVM-native `Keccak256`), and classifies `VERIFIED / HASH_MISMATCH / UNREACHABLE`. The retrieved content excerpt and integrity result are fed to the LLM reasoning step.
3. **Evidence-Gated Verdict Policy:**
   `FREELANCER` (full award) is only possible when evidence integrity is `VERIFIED`; otherwise the verdict is deterministically downgraded to `SPLIT`. The policy is enforced both inside the consensus closure and post-consensus on-chain (defense in depth).
4. **Deterministic Equivalence Principle Consensus (`strict_eq`):**
   Non-deterministic natural-language reasoning is isolated in `gl.nondet.exec_prompt`. Validator committees evaluate deliverable fulfillment against the requirement brief and reach semantic consensus on fund allocation (`FREELANCER`, `CLIENT`, or `SPLIT`) plus the normalized evidence status. To prevent validator rotation timeouts from subtle text variances, verdict normalization occurs before strict equivalence hashing.
5. **Storage Boundary Enforcement:**
   Storage data is strictly copied into local string primitives before entering non-deterministic closures, preventing GenVM sub-VM pickling warnings and memory sandbox violations.

---

## 🛡️ Security Invariants & Access Control

* **Invariant 1 (Collision Resistance):** `create_case` verifies `case_id not in self.cases` to prevent malicious overwrites of active or settled case records.
* **Invariant 1b (No Self-Dealing):** `create_case` rejects `freelancer == sender`, preventing a single actor from fabricating a two-party "AI-resolved" dispute record.
* **Invariant 2 (Deliverable Authorization):** `submit_deliverable` enforces caller verification (`sender == case.freelancer or sender == case.client`), preventing third-party deliverable tampering.
* **Invariant 2b (Evidence Commitment Guards):** `submit_deliverable` requires an `https://` evidence URL (≤512 chars) and a 64-char hex `keccak256` digest — evidence-free submissions are rejected at the contract level.
* **Invariant 3 (Adjudication Gating):** `adjudicate_dispute` restricts callers to registered contract parties (`sender == case.client or sender == case.freelancer`) and requires `status == "SUBMITTED"` to prevent premature adjudication on empty proofs.
* **Invariant 3b (Evidence-Gated Award):** full `FREELANCER` awards are unreachable unless the artifact re-fetches with a matching `keccak256` (`VERIFIED`); `HASH_MISMATCH` / `UNREACHABLE` deterministically downgrade the verdict to `SPLIT`.
* **Invariant 4 (Finite State Machine):** Cases transition strictly `CREATED -> SUBMITTED -> RESOLVED`. No retroactive mutations or double-adjudications are permitted once settled.

---

## 📜 Verified Deployments

| Network | Chain ID | Contract Address | Status | Explorer |
| :--- | :--- | :--- | :--- | :--- |
| **GenLayer Asimov Testnet (v1.4.0)** | 4221 | `0x3959A1B0e1a8aebEAeBf6f7eEA0279BDaaD98eFF` | Finalized (`FINISHED_WITH_RETURN`) | [View on Asimov Explorer](https://explorer-asimov.genlayer.com/address/0x3959A1B0e1a8aebEAeBf6f7eEA0279BDaaD98eFF) |
| **GenLayer Asimov Testnet (v1.3.0)** | 4221 | `0x498a595eE9F003F1b6cB585B322470a583F09684` | Finalized (`FINISHED_WITH_RETURN`) | [View on Asimov Explorer](https://explorer-asimov.genlayer.com/address/0x498a595eE9F003F1b6cB585B322470a583F09684) |

### On-Chain Transaction Proofs (v1.4.0 — Contract-Side Evidence Retrieval & Validation):
* **Contract Deploy:** [`0x11f4a2431ee915c474e639a15598168e6ef6403ff8b02b46d8bf46d5d8521ddc`](https://explorer-asimov.genlayer.com/tx/0x11f4a2431ee915c474e639a15598168e6ef6403ff8b02b46d8bf46d5d8521ddc) -> `FINISHED_WITH_RETURN`
* **Self-Dealing Guard (Invariant 1b):** [`0xccd8d7cd090dbf5d08f38aab09c9d6c91ae06c5887d28c004dee9c2f7ab1e021`](https://explorer-asimov.genlayer.com/tx/0xccd8d7cd090dbf5d08f38aab09c9d6c91ae06c5887d28c004dee9c2f7ab1e021) -> `create_case` with `freelancer == sender` finalized with failed execution and **no state change** (`selfdeal_neg` absent from storage, total_cases unchanged).
* **Create Case:** [`0x8bd66d734b3bfbb90c0f2157ce96327898390424123dc1c010b742254859afc4`](https://explorer-asimov.genlayer.com/tx/0x8bd66d734b3bfbb90c0f2157ce96327898390424123dc1c010b742254859afc4) -> `FINISHED_WITH_RETURN` (case `case_v14_01`).
* **Submit Deliverable + Evidence Commitment:** [`0xd48638086e835925bec62663063814dfe01cf53471a9222170132ee55b04ae48`](https://explorer-asimov.genlayer.com/tx/0xd48638086e835925bec62663063814dfe01cf53471a9222170132ee55b04ae48) -> `FINISHED_WITH_RETURN` (commits raw GitHub artifact URL + keccak256 digest `e2d94f69...b35931`).
* **AI Consensus Adjudication (RESOLVED):** [`0xa232e8e2216f12625641fb500f8a673be7abdbdc08bde9dae7bb340ab6d7f083`](https://explorer-asimov.genlayer.com/tx/0xa232e8e2216f12625641fb500f8a673be7abdbdc08bde9dae7bb340ab6d7f083) -> Consensus reached (`AGREE`), case finalized to `RESOLVED`:
  - **Verdict:** `CLIENT` (100% client refund)
  - **Evidence Status:** `VERIFIED` (contract re-fetched raw artifact from GitHub and confirmed `keccak256` digest matched on-chain commitment)
  - **Reason:** `"Consensus by GenLayer validators: CLIENT (100% refund to client); evidence VERIFIED"`

### Prior Version Proofs (v1.3.0):
* **Contract Deploy:** [`0x331bc289302f0ec70a95018a0ac5a590dbecbed8c080a414e88f09acc0e845d4`](https://explorer-asimov.genlayer.com/tx/0x331bc289302f0ec70a95018a0ac5a590dbecbed8c080a414e88f09acc0e845d4)
* **AI Consensus Adjudication:** [`0x7ea4ea1e0b14a754647e4a2980b3e74efd4e8fc537cacfa6b8ee5aa938c1f175`](https://explorer-asimov.genlayer.com/tx/0x7ea4ea1e0b14a754647e4a2980b3e74efd4e8fc537cacfa6b8ee5aa938c1f175) -> `RESOLVED / FREELANCER / 0% client share`

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

Coverage (11 tests): initial state, create/get, case-ID collision, self-dealing rejection, third-party submit/adjudicate rejection, premature adjudication rejection, evidence-commitment guards (bad URL / bad hash), full lifecycle with **verified evidence** (`mock_web` + `mock_llm` → `FREELANCER`), **hash-mismatch downgrade** (`HASH_MISMATCH` → `SPLIT`), **unreachable-evidence downgrade** (`UNREACHABLE` → `SPLIT`), non-JSON LLM response falling back to `SPLIT`, and post-resolve immutability.
