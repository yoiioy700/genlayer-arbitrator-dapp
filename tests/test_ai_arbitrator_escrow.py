# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from genlayer.testing import direct_mode
import pytest


def test_initial_state():
    """Verify initial contract state has 0 cases."""
    with direct_mode() as dm:
        contract = dm.deploy("contracts/AIArbitratorEscrow.py")
        count = dm.call(contract, "get_total_cases")
        assert count == 0


def test_create_and_get_case():
    """Verify case creation and storage retrieval."""
    with direct_mode() as dm:
        contract = dm.deploy("contracts/AIArbitratorEscrow.py")
        case_id = dm.call(
            contract,
            "create_case",
            "case_test_01",
            "0x1111111111111111111111111111111111111111",
            1000000000000000000,
            "Develop responsive frontend dApp for GenLayer escrow with verification"
        )
        assert case_id == "case_test_01"

        case_data = dm.call(contract, "get_case", "case_test_01")
        assert case_data["case_id"] == "case_test_01"
        assert case_data["status"] == "CREATED"
        assert case_data["verdict"] == "PENDING"
        assert case_data["amount"] == 1000000000000000000


def test_case_collision_rejected():
    """Verify that duplicate case_id cannot overwrite existing active escrow."""
    with direct_mode() as dm:
        contract = dm.deploy("contracts/AIArbitratorEscrow.py")
        dm.call(
            contract,
            "create_case",
            "case_test_duplicate",
            "0x1111111111111111111111111111111111111111",
            100,
            "Initial valid requirements for first case registration"
        )

        with pytest.raises(Exception, match="Case ID already exists"):
            dm.call(
                contract,
                "create_case",
                "case_test_duplicate",
                "0x2222222222222222222222222222222222222222",
                200,
                "Malicious overwrite attempt with new requirements"
            )


def test_adjudicate_unsubmitted_rejected():
    """Verify that dispute adjudication cannot proceed before deliverable is submitted."""
    with direct_mode() as dm:
        contract = dm.deploy("contracts/AIArbitratorEscrow.py")
        dm.call(
            contract,
            "create_case",
            "case_premature",
            "0x1111111111111111111111111111111111111111",
            100,
            "Valid requirements waiting for deliverable submission"
        )

        with pytest.raises(Exception, match="Deliverable must be submitted"):
            dm.call(contract, "adjudicate_dispute", "case_premature")
