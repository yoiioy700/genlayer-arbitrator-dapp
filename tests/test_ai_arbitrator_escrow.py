"""Tests for AIArbitratorEscrow using gltest direct mode (genlayer-test >= 0.29).

Run: .venv/bin/python -m pytest tests/ -q
"""
import pytest

CONTRACT = "contracts/AIArbitratorEscrow.py"


def hex_addr(a) -> str:
    """Direct-mode addresses are raw bytes; production sends hex strings."""
    return "0x" + bytes(a).hex()
REQ = "Develop responsive frontend dApp for GenLayer escrow with verification"


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
    """Invariants 2 & 3: only case parties may submit deliverable / adjudicate."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice  # client
    contract.create_case("case_tp", hex_addr(direct_bob), 100, REQ)
    direct_vm.sender = direct_bob  # freelancer
    contract.submit_deliverable("case_tp", "Delivered: repo with passing tests")

    direct_vm.sender = direct_charlie  # outsider
    with direct_vm.expect_revert("Only freelancer or client"):
        contract.submit_deliverable("case_tp", "spoofed deliverable")
    with direct_vm.expect_revert("Only client or freelancer"):
        contract.adjudicate_dispute("case_tp")


def test_adjudicate_unsubmitted_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT)
    contract.create_case("case_premature", hex_addr(direct_bob), 100, REQ)
    with direct_vm.expect_revert("Deliverable must be submitted"):
        contract.adjudicate_dispute("case_premature")


def test_adjudicate_happy_path_freeslancer(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Full lifecycle CREATED -> SUBMITTED -> RESOLVED with mocked LLM consensus."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_ai", hex_addr(direct_bob), 1000, REQ)
    direct_vm.sender = direct_bob
    contract.submit_deliverable("case_ai", "Delivered repo github.com/x/y, all tests pass")

    direct_vm.sender = direct_alice
    direct_vm.mock_llm("decentralized dispute arbitrator", '{"verdict": "FREELANCER"}')
    res = contract.adjudicate_dispute("case_ai")
    assert res["verdict"] == "FREELANCER"
    assert res["client_share_pct"] == 0

    case = contract.get_case("case_ai")
    assert case["status"] == "RESOLVED"
    assert case["client_share_pct"] == 0

    # Invariant 4: resolved case is immutable
    with direct_vm.expect_revert("resolved case"):
        contract.submit_deliverable("case_ai", "late deliverable")
    with direct_vm.expect_revert("already been adjudicated"):
        contract.adjudicate_dispute("case_ai")


def test_adjudicate_llm_garbage_falls_back_split(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Non-JSON validator response falls back to SPLIT instead of reverting (F4)."""
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    contract.create_case("case_garbage", hex_addr(direct_bob), 1000, REQ)
    contract.submit_deliverable("case_garbage", "some deliverable text")

    direct_vm.mock_llm("decentralized dispute arbitrator", "not-json at all <<<>>>")
    res = contract.adjudicate_dispute("case_garbage")
    assert res["verdict"] == "SPLIT"
    assert res["client_share_pct"] == 50
