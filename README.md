# AI Arbitrator Escrow - GenLayer Intelligent Contract & dApp

A decentralized, autonomous freelance escrow and dispute adjudication platform built on **GenLayer**.

When clients and freelancers face milestone disagreements, GenLayer AI validators independently evaluate the agreed job requirements against submitted deliverables to reach consensus on payout distribution via the **Equivalence Principle** (`gl.eq_principle.strict_eq`).

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

* **Invariant 1 (Collision Resistance):** `create_case` verifies `case_id not in self.cases` to prevent malicious overwrites of active or settled escrow deposits.
* **Invariant 2 (Deliverable Authorization):** `submit_deliverable` enforces caller verification (`sender == case.freelancer or sender == case.client`), preventing third-party deliverable tampering.
* **Invariant 3 (Adjudication Gating):** `adjudicate_dispute` restricts callers to registered contract parties (`sender == case.client or sender == case.freelancer`) and requires `status == "SUBMITTED"` to prevent premature adjudication on empty proofs.
* **Invariant 4 (Finite State Machine):** Cases transition strictly `CREATED -> SUBMITTED -> RESOLVED`. No retroactive mutations or double-adjudications are permitted once settled.

---

## 📜 Verified Deployments

| Network | Chain ID | Contract Address | Status | Explorer |
| :--- | :--- | :--- | :--- | :--- |
| **GenLayer Asimov Testnet** | 4221 | `0xe822FA3A2b6aA657EddBEbbFF8dC1F9926695e36` | Finalized (`FINISHED_WITH_RETURN`) | [View on Asimov Explorer](https://explorer-asimov.genlayer.com/address/0xe822FA3A2b6aA657EddBEbbFF8dC1F9926695e36) |

### On-Chain Transaction Proofs:
* **Contract Deploy:** [`0xef703e0cc9ecd9ff9b2484f02d907c4be7b2d55a8a2d17b5fa770b1de2cf4308`](https://explorer-asimov.genlayer.com/tx/0xef703e0cc9ecd9ff9b2484f02d907c4be7b2d55a8a2d17b5fa770b1de2cf4308)
* **Create Case Tx:** [`0x586510d1a4a368f751c5078cda6c3dc1c30ef8d1adfc9163daa2503924617430`](https://explorer-asimov.genlayer.com/tx/0x586510d1a4a368f751c5078cda6c3dc1c30ef8d1adfc9163daa2503924617430)
* **Submit Deliverable Tx:** [`0xaa359af6a77e621836f896227a1a536fea505b740b2b8aac857a94adb9c97c0c`](https://explorer-asimov.genlayer.com/tx/0xaa359af6a77e621836f896227a1a536fea505b740b2b8aac857a94adb9c97c0c)
* **AI Consensus Adjudication Tx (RESOLVED):** [`0x5e212ffca4c4191924e456da0eb509787c8897401f258481d3d87ddcbd1446a3`](https://explorer-asimov.genlayer.com/tx/0x5e212ffca4c4191924e456da0eb509787c8897401f258481d3d87ddcbd1446a3)

---

## 💻 Running the Frontend

The dApp frontend is built with **Next.js 16 (Turbopack)** and directly uses `genlayer-js` to connect to GenLayer Asimov:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to create escrow cases, submit deliverables, and trigger AI arbitrator adjudication.

---

## 🧪 Unit Tests

Run direct-mode test suites:
```bash
pytest tests/
```
