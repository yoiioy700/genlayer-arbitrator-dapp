"""Tests for AIArbitratorEscrow v1.4 (contract-side evidence retrieval & validation).

Run: .venv/bin/python -m pytest tests/ -q
"""
import pytest
from eth_hash.auto import keccak

CONTRACT = "contracts/AIArbitratorEscrow.py"


def hex_addr(a) -> str:
    """Direct-mode addresses are raw bytes; production sends hex strings."""
    return "0x" + bytes(a).hex()


REQ = "Develop responsive frontend dApp for GenLayer escrow with verification"

BODY = "DELIVERABLE-ARTIFACT-v1: repo commit abc123; all tests passing"
URL = "https://raw.githubusercontent.com/example/repo/main/artifact.txt"
HASH = keccak(BODY.encode()).hex()


def test_initial_state(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    assert contract.get_total_cases() == 0


def test_create_and_get_case(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    contract.create_case("case_test_01", hex_addr(direct_alice), 10**18, REQ)
    case = contract.get_case("case_test_01")
    assert case["case_id"] == "case_test_01"
    assert case["status"] == "CREATED"
    assert case["verdict"] == "PENDING"
    assert case["amount"] == 10**18
    assert case["evidence_status"] == ""
    assert contract.get_total_cases() == 1


def test_case_collision_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT)
    contract.create_case("dup", hex_addr(direct_alice), 100, REQ)
    with direct_vm.expect_revert("Case ID already exists"):
        contract.create_case(
            "dup", hex_addr(direct_bob), 200, "Malicious overwrite attempt with new requirements"
        )


def test_self_dealing_rejected(direct_vm, direct_deploy, direct_alice):
    """Invariant 1b: freelancer == client (sender) must be rejected."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("same address"):
        contract.create_case("selfdeal", hex_addr(direct_alice), 100, REQ)


def test_third_party_cannot_submit_or_adjudicate(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    """Invariants 2 & 4: only case parties may submit deliverable / adjudicate."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice  # client
    contract.create_case("case_tp", hex_addr(direct_bob), 100, REQ)
    direct_vm.sender = direct_bob  # freelancer
    contract.submit_deliverable("case_tp", "Delivered: repo with passing tests", URL, HASH)

    direct_vm.sender = direct_charlie  # outsider
    with direct_vm.expect_revert("Only freelancer or client"):
        contract.submit_deliverable("case_tp", "spoofed deliverable", URL, HASH)
    with direct_vm.expect_revert("Only client or freelancer"):
        contract.adjudicate_dispute("case_tp")


def test_adjudicate_unsubmitted_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT)
    contract.create_case("case_premature", hex_addr(direct_bob), 100, REQ)
    with direct_vm.expect_revert("Deliverable must be submitted"):
        contract.adjudicate_dispute("case_premature")


def test_submit_requires_valid_evidence_commitment(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Evidence guards: https-only URL + 64-char hex keccak256 digest."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_ev", hex_addr(direct_bob), 100, REQ)
    direct_vm.sender = direct_bob

    with direct_vm.expect_revert("https:// URL"):
        contract.submit_deliverable("case_ev", "delivered", "http://insecure.example.com/x", HASH)
    with direct_vm.expect_revert("64-char hex keccak256"):
        contract.submit_deliverable("case_ev", "delivered", URL, "abc123")
    with direct_vm.expect_revert("64-char hex keccak256"):
        contract.submit_deliverable("case_ev", "delivered", URL, "zz" * 32)

    # Failed attempts changed nothing; a correct commitment still works.
    case = contract.get_case("case_ev")
    assert case["status"] == "CREATED"
    contract.submit_deliverable("case_ev", "delivered", URL, HASH.upper())  # hex case-insensitive
    case = contract.get_case("case_ev")
    assert case["status"] == "SUBMITTED"
    assert case["evidence_hash"] == HASH


def test_full_lifecycle_evidence_verified_freelancer(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Happy path: contract fetches evidence, keccak256 matches, verdict FREELANCER."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_v14_ok", hex_addr(direct_bob), 1000, REQ)
    direct_vm.sender = direct_bob
    contract.submit_deliverable("case_v14_ok", "Artifact uploaded to repo", URL, HASH)

    direct_vm.mock_web(URL, {"status": 200, "body": BODY})
    direct_vm.mock_llm("dispute arbitrator", '{"verdict": "FREELANCER"}')

    direct_vm.sender = direct_alice
    res = contract.adjudicate_dispute("case_v14_ok")
    assert res["verdict"] == "FREELANCER"
    assert res["client_share_pct"] == 0
    assert res["evidence_status"] == "VERIFIED"

    case = contract.get_case("case_v14_ok")
    assert case["status"] == "RESOLVED"
    assert case["evidence_status"] == "VERIFIED"
    assert case["evidence_url"] == URL
    assert case["evidence_hash"] == HASH

    # Invariants: resolved case is immutable
    with direct_vm.expect_revert("resolved case"):
        contract.submit_deliverable("case_v14_ok", "late deliverable", URL, HASH)
    with direct_vm.expect_revert("already been adjudicated"):
        contract.adjudicate_dispute("case_v14_ok")


def test_hash_mismatch_downgrades_freelancer_to_split(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Tampered artifact: keccak mismatch -> cached FREELANCER is downgraded to SPLIT."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_v14_tamper", hex_addr(direct_bob), 1000, REQ)
    direct_vm.sender = direct_bob
    contract.submit_deliverable("case_v14_tamper", "claim", URL, HASH)

    direct_vm.mock_web(URL, {"status": 200, "body": "TAMPERED CONTENT"})
    direct_vm.mock_llm("dispute arbitrator", '{"verdict": "FREELANCER"}')

    res = contract.adjudicate_dispute("case_v14_tamper")
    assert res["evidence_status"] == "HASH_MISMATCH"
    assert res["verdict"] == "SPLIT"
    assert res["client_share_pct"] == 50

    case = contract.get_case("case_v14_tamper")
    assert case["evidence_status"] == "HASH_MISMATCH"
    assert case["status"] == "RESOLVED"


def test_unreachable_evidence_downgrades_to_split(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Fetch failure (no content): evidence UNREACHABLE, no full award."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_v14_offline", hex_addr(direct_bob), 1000, REQ)
    direct_vm.sender = direct_bob
    contract.submit_deliverable("case_v14_offline", "claim", URL, HASH)

    # No web mock registered -> retrieval raises inside the closure and is caught.
    direct_vm.mock_llm("dispute arbitrator", '{"verdict": "FREELANCER"}')

    res = contract.adjudicate_dispute("case_v14_offline")
    assert res["evidence_status"] == "UNREACHABLE"
    assert res["verdict"] == "SPLIT"
    assert res["client_share_pct"] == 50


def test_llm_garbage_falls_back_split(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Non-JSON validator response falls back to SPLIT instead of reverting."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_garbage", hex_addr(direct_bob), 1000, REQ)
    direct_vm.sender = direct_bob
    contract.submit_deliverable("case_garbage", "some deliverable text", URL, HASH)

    direct_vm.mock_web(URL, {"status": 200, "body": BODY})
    direct_vm.mock_llm("dispute arbitrator", "not-json at all <<<>>>")

    res = contract.adjudicate_dispute("case_garbage")
    assert res["verdict"] == "SPLIT"
    assert res["client_share_pct"] == 50
