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
    status: str  # "CREATED", "SUBMITTED", "RESOLVED"
    verdict: str  # "CLIENT", "FREELANCER", "SPLIT"
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
        
        new_case = DisputeCase(
            case_id=case_id,
            client=client_addr,
            freelancer=freelancer,
            amount=u256(int(amount_wei)),
            requirements=requirements,
            deliverable="",
            status="CREATED",
            verdict="PENDING",
            client_share_pct=u256(0),
            reason=""
        )
        self.cases[case_id] = new_case
        self.total_cases = u256(int(self.total_cases) + 1)
        return case_id

    @gl.public.write
    def submit_deliverable(self, case_id: str, deliverable: str) -> None:
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

        case.deliverable = deliverable
        case.status = "SUBMITTED"
        self.cases[case_id] = case

    @gl.public.write
    def adjudicate_dispute(self, case_id: str) -> dict:
        if case_id not in self.cases:
            raise gl.vm.UserError("Case does not exist")

        case = self.cases[case_id]

        # Invariant 4: Access Control - Only parties to the escrow can request adjudication
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

        def evaluate_case() -> str:
            prompt = f"""You are a decentralized dispute arbitrator evaluating a freelance delivery.

Requirements:
{req_text}

Submitted Deliverable:
{deliv_text}

Analyze whether the deliverable fulfills the agreed requirements.
Decide the verdict:
- "FREELANCER" if requirements are fully or substantially met.
- "CLIENT" if deliverable is entirely missing, fraudulent, or failed.
- "SPLIT" if partially completed.

Respond ONLY with valid JSON with this schema:
{{
    "verdict": "FREELANCER" | "CLIENT" | "SPLIT"
}}
"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            raw_v = str(res.get("verdict", "SPLIT")).strip().upper()
            if raw_v not in ["FREELANCER", "CLIENT", "SPLIT"]:
                raw_v = "SPLIT"

            pct = 0 if raw_v == "FREELANCER" else (100 if raw_v == "CLIENT" else 50)
            return json.dumps({"verdict": raw_v, "client_share_pct": pct}, sort_keys=True)

        # Reach consensus across validator committee using Equivalence Principle
        consensus_res_str = gl.eq_principle.strict_eq(evaluate_case)
        result = json.loads(consensus_res_str)

        verdict = result.get("verdict", "SPLIT")
        pct = int(result.get("client_share_pct", 50))

        case.verdict = verdict
        case.client_share_pct = u256(pct)
        case.reason = f"Consensus reached by GenLayer validators: {verdict} ({pct}% refund to client)"
        case.status = "RESOLVED"
        self.cases[case_id] = case

        return {
            "verdict": verdict,
            "client_share_pct": pct,
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
            "status": case.status,
            "verdict": case.verdict,
            "client_share_pct": int(case.client_share_pct),
            "reason": case.reason
        }

    @gl.public.view
    def get_total_cases(self) -> int:
        return int(self.total_cases)
