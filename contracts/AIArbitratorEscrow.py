# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class DisputeCase:
    case_id: str
    client: Address
    freelancer: Address
    amount: u256
    requirements: str
    deliverable: str
    evidence_url: str
    evidence_hash: str
    evidence_status: str  # "", "VERIFIED", "HASH_MISMATCH", "UNREACHABLE"
    status: str  # "CREATED", "SUBMITTED", "RESOLVED"
    verdict: str  # "PENDING", "CLIENT", "FREELANCER", "SPLIT"
    client_share_pct: u256
    reason: str


class AIArbitratorEscrow(gl.Contract):
    cases: TreeMap[str, DisputeCase]
    total_cases: u256

    def __init__(self):
        self.cases = TreeMap()
        self.total_cases = u256(0)

    @gl.public.write
    def create_case(
        self,
        case_id: str,
        freelancer_addr: str,
        amount_wei: u256,
        requirements: str
    ) -> str:
        # Invariant 1: Prevent case collision / overwrite attack
        if case_id in self.cases:
            raise gl.vm.UserError("Case ID already exists")

        if len(case_id.strip()) == 0:
            raise gl.vm.UserError("Case ID cannot be empty")

        if len(requirements.strip()) < 10:
            raise gl.vm.UserError("Requirements must be at least 10 characters")

        client_addr = gl.message.sender_address
        freelancer = Address(freelancer_addr) if isinstance(freelancer_addr, (str, bytes)) else freelancer_addr

        # Invariant 1b: No self-dealing — a single actor cannot fabricate a two-party dispute
        if freelancer == client_addr:
            raise gl.vm.UserError("Client and freelancer cannot be the same address")

        new_case = DisputeCase(
            case_id=case_id,
            client=client_addr,
            freelancer=freelancer,
            amount=u256(int(amount_wei)),
            requirements=requirements,
            deliverable="",
            evidence_url="",
            evidence_hash="",
            evidence_status="",
            status="CREATED",
            verdict="PENDING",
            client_share_pct=u256(0),
            reason=""
        )
        self.cases[case_id] = new_case
        self.total_cases = u256(int(self.total_cases) + 1)
        return case_id

    @gl.public.write
    def submit_deliverable(
        self,
        case_id: str,
        deliverable: str,
        evidence_url: str,
        evidence_hash: str
    ) -> None:
        if case_id not in self.cases:
            raise gl.vm.UserError("Case does not exist")

        case = self.cases[case_id]

        # Invariant 2: Access Control - Only designated freelancer or client can submit
        sender = gl.message.sender_address
        if sender != case.freelancer and sender != case.client:
            raise gl.vm.UserError("Only freelancer or client can submit deliverable")

        # Invariant 3: State machine - Cannot update after final resolution
        if case.status == "RESOLVED":
            raise gl.vm.UserError("Cannot submit deliverable to a resolved case")

        if len(deliverable.strip()) == 0:
            raise gl.vm.UserError("Deliverable cannot be empty")

        # Evidence commitment guards: the freelancer must anchor a fetchable artifact
        # (https) to a keccak256 digest. Validators will re-fetch and verify it.
        url = str(evidence_url).strip()
        h = str(evidence_hash).strip().lower()

        if len(url) < 12 or len(url) > 512 or not url.startswith("https://"):
            raise gl.vm.UserError("Evidence URL must be an https:// URL (max 512 chars)")

        hash_ok = len(h) == 64
        if hash_ok:
            for c in h:
                if c not in "0123456789abcdef":
                    hash_ok = False
                    break
        if not hash_ok:
            raise gl.vm.UserError("Evidence hash must be a 64-char hex keccak256 digest")

        case.deliverable = deliverable
        case.evidence_url = url
        case.evidence_hash = h
        case.status = "SUBMITTED"
        self.cases[case_id] = case

    @gl.public.write
    def adjudicate_dispute(self, case_id: str) -> dict:
        if case_id not in self.cases:
            raise gl.vm.UserError("Case does not exist")

        case = self.cases[case_id]

        # Invariant 4: Access Control - Only parties to the record can request adjudication
        sender = gl.message.sender_address
        if sender != case.client and sender != case.freelancer:
            raise gl.vm.UserError("Only client or freelancer can request adjudication")

        # Invariant 5: State machine - Must have deliverable submitted & not yet resolved
        if case.status == "RESOLVED":
            raise gl.vm.UserError("Case has already been adjudicated and resolved")

        if case.status != "SUBMITTED":
            raise gl.vm.UserError("Deliverable must be submitted before dispute adjudication")

        # Extract storage values to local primitive strings before nondet execution
        req_text = str(case.requirements)
        deliv_text = str(case.deliverable)
        url = str(case.evidence_url)
        expected_hash = str(case.evidence_hash)

        def evaluate_case() -> str:
            # --- Evidence retrieval & validation (contract-side, per validator) ---
            evidence_status = "UNREACHABLE"
            excerpt = ""
            try:
                resp = gl.nondet.web.get(url)
                if resp is not None and int(resp.status) == 200 and resp.body is not None and len(resp.body) > 0:
                    raw = bytes(resp.body)
                    actual_hash = Keccak256(raw).hexdigest()
                    if actual_hash.lower() == expected_hash:
                        evidence_status = "VERIFIED"
                    else:
                        evidence_status = "HASH_MISMATCH"
                    excerpt = raw.decode("utf-8", errors="replace")[:4000]
            except Exception:
                evidence_status = "UNREACHABLE"

            # --- Reasoning over requirements + claim + retrieved evidence ---
            prompt = f"""You are a decentralized dispute arbitrator evaluating a freelance delivery. Independent validators will run you separately and must agree on the verdict.

Agreed requirements:
{req_text}

Deliverable submitted by the freelancer (party claim, text only):
{deliv_text}

Evidence retrieved by the contract itself from {url}
(integrity check result: {evidence_status}):
{excerpt if excerpt else "(no content could be retrieved)"}

Decide the verdict:
- "FREELANCER" only if the delivered work substantially meets the requirements AND evidence integrity is VERIFIED.
- "CLIENT" if the deliverable is missing, fraudulent, or fails the requirements (a HASH_MISMATCH indicates tampering with the committed artifact).
- "SPLIT" if only partially completed, or if the evidence cannot be verified.

Respond ONLY with valid JSON with this schema:
{{
    "verdict": "FREELANCER" | "CLIENT" | "SPLIT"
}}
"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}
            raw_v = str(res.get("verdict", "SPLIT")).strip().upper()
            if raw_v not in ["FREELANCER", "CLIENT", "SPLIT"]:
                raw_v = "SPLIT"

            # Evidence-gated settlement policy: a full award requires a verified artifact.
            if raw_v == "FREELANCER" and evidence_status != "VERIFIED":
                raw_v = "SPLIT"

            pct = 0 if raw_v == "FREELANCER" else (100 if raw_v == "CLIENT" else 50)
            return json.dumps(
                {"verdict": raw_v, "client_share_pct": pct, "evidence_status": evidence_status},
                sort_keys=True
            )

        # Reach consensus across the validator committee using the Equivalence Principle
        consensus_res_str = gl.eq_principle.strict_eq(evaluate_case)
        try:
            result = json.loads(consensus_res_str)
            if not isinstance(result, dict):
                result = {}
        except (json.JSONDecodeError, TypeError):
            result = {}

        verdict = str(result.get("verdict", "SPLIT"))
        if verdict not in ["FREELANCER", "CLIENT", "SPLIT"]:
            verdict = "SPLIT"
        pct = int(result.get("client_share_pct", 50))
        if pct not in (0, 50, 100):
            pct = 50
        ev_status = str(result.get("evidence_status", "UNREACHABLE"))
        if ev_status not in ["VERIFIED", "HASH_MISMATCH", "UNREACHABLE"]:
            ev_status = "UNREACHABLE"

        # Defense in depth: enforce the evidence-gating policy on-chain as well.
        if verdict == "FREELANCER" and ev_status != "VERIFIED":
            verdict = "SPLIT"
            pct = 50

        case.verdict = verdict
        case.client_share_pct = u256(pct)
        case.evidence_status = ev_status
        case.reason = f"Consensus by GenLayer validators: {verdict} ({pct}% refund to client); evidence {ev_status}"
        case.status = "RESOLVED"
        self.cases[case_id] = case

        return {
            "verdict": verdict,
            "client_share_pct": pct,
            "evidence_status": ev_status,
            "reason": case.reason
        }

    @gl.public.view
    def get_case(self, case_id: str) -> dict:
        if case_id not in self.cases:
            raise gl.vm.UserError("Case does not exist")

        case = self.cases[case_id]
        return {
            "case_id": case.case_id,
            "client": str(case.client),
            "freelancer": str(case.freelancer),
            "amount": int(case.amount),
            "requirements": case.requirements,
            "deliverable": case.deliverable,
            "evidence_url": case.evidence_url,
            "evidence_hash": case.evidence_hash,
            "evidence_status": case.evidence_status,
            "status": case.status,
            "verdict": case.verdict,
            "client_share_pct": int(case.client_share_pct),
            "reason": case.reason
        }

    @gl.public.view
    def get_total_cases(self) -> int:
        return int(self.total_cases)
