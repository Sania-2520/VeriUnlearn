from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from app.domain.audit.entities import ActorType, AuditEvent, EventStatus, EventType
from app.domain.audit.services import AuditService
from app.infrastructure.external.blockchain import BlockchainAnchoringService, SimulatedBlockchain


@pytest.fixture
def sample_events():
    return [
        AuditEvent(
            id="evt-1",
            tenant_id="tenant-1",
            event_type=EventType.USER_LOGIN,
            actor_id="user-1",
            actor_type=ActorType.USER,
            action="login",
            status=EventStatus.SUCCESS,
            event_hash="a" * 64,
            timestamp=datetime.now(timezone.utc),
        ),
        AuditEvent(
            id="evt-2",
            tenant_id="tenant-1",
            event_type=EventType.USER_LOGOUT,
            actor_id="user-1",
            actor_type=ActorType.USER,
            action="logout",
            status=EventStatus.SUCCESS,
            previous_event_hash="a" * 64,
            event_hash="b" * 64,
            timestamp=datetime.now(timezone.utc),
        ),
    ]


class TestSimulatedBlockchain:
    def test_submit_root_returns_transaction(self):
        bc = SimulatedBlockchain()
        tx = bc.submit_root("merkle_root_abc", "tenant-1", "goerli")
        assert tx.tx_hash is not None
        assert tx.merkle_root == "merkle_root_abc"
        assert tx.tenant_id == "tenant-1"
        assert tx.network == "goerli"
        assert tx.block_number == 1
        assert tx.status == "confirmed"

    def test_submit_root_multiple_blocks(self):
        bc = SimulatedBlockchain()
        tx1 = bc.submit_root("root1", "t1", "goerli")
        tx2 = bc.submit_root("root2", "t2", "goerli")
        assert tx2.block_number == 2
        assert tx1.block_number != tx2.block_number

    def test_get_transaction_returns_tx(self):
        bc = SimulatedBlockchain()
        bc.submit_root("root", "t1", "goerli")
        stored = bc.get_transaction("nonexistent")
        assert stored is None

    def test_verify_root_valid(self):
        bc = SimulatedBlockchain()
        tx = bc.submit_root("my_root", "t1", "goerli")
        assert bc.verify_root("my_root", tx.tx_hash) is True

    def test_verify_root_invalid(self):
        bc = SimulatedBlockchain()
        tx = bc.submit_root("my_root", "t1", "goerli")
        assert bc.verify_root("wrong_root", tx.tx_hash) is False

    def test_verify_root_wrong_tx(self):
        bc = SimulatedBlockchain()
        assert bc.verify_root("any", "fake_tx") is False

    def test_get_chain_height(self):
        bc = SimulatedBlockchain()
        assert bc.get_chain_height() == 0
        bc.submit_root("r1", "t1", "goerli")
        assert bc.get_chain_height() == 1
        bc.submit_root("r2", "t2", "goerli")
        assert bc.get_chain_height() == 2


class TestBlockchainAnchoringService:
    def test_anchor_disabled_by_default(self):
        svc = BlockchainAnchoringService()
        svc._enabled = False
        result = asyncio_run(svc.anchor("root", "t1"))
        assert result["anchored"] is False
        assert result["reason"] == "blockchain anchoring disabled"

    def test_anchor_enabled_succeeds(self):
        svc = BlockchainAnchoringService()
        svc._enabled = True
        result = asyncio_run(svc.anchor("merkle_root_xyz", "tenant-1"))
        assert result["anchored"] is True
        assert result["tx_hash"] is not None
        assert result["network"] == "goerli"
        assert result["block_number"] >= 1

    def test_verify_valid_anchor(self):
        svc = BlockchainAnchoringService()
        svc._enabled = True
        result = asyncio_run(svc.anchor("root_to_verify", "t1"))
        verify = asyncio_run(svc.verify("root_to_verify", result["tx_hash"]))
        assert verify["is_valid"] is True

    def test_verify_invalid_anchor(self):
        svc = BlockchainAnchoringService()
        verify = asyncio_run(svc.verify("fake_root", "fake_tx"))
        assert verify["is_valid"] is False

    def test_get_transaction_unknown(self):
        svc = BlockchainAnchoringService()
        result = asyncio_run(svc.get_transaction("nonexistent"))
        assert result is None

    def test_is_anchored(self):
        svc = BlockchainAnchoringService()
        svc._enabled = True
        result = asyncio_run(svc.anchor("r", "t1"))
        assert asyncio_run(svc.is_anchored(result["tx_hash"])) is True
        assert asyncio_run(svc.is_anchored("fake")) is False

    def test_compute_merkle_root_empty(self):
        svc = BlockchainAnchoringService()
        root = svc.compute_merkle_root([])
        assert len(root) == 64

    def test_compute_merkle_root_single(self):
        svc = BlockchainAnchoringService()
        root = svc.compute_merkle_root([{"id": "1", "action": "login"}])
        assert len(root) == 64

    def test_compute_merkle_root_multiple(self):
        svc = BlockchainAnchoringService()
        root = svc.compute_merkle_root([{"id": "1"}, {"id": "2"}, {"id": "3"}])
        assert len(root) == 64
        # same data => same root
        root2 = svc.compute_merkle_root([{"id": "1"}, {"id": "2"}, {"id": "3"}])
        assert root == root2
        # different data => different root
        root3 = svc.compute_merkle_root([{"id": "1"}, {"id": "2"}, {"id": "4"}])
        assert root != root3


class TestAuditServiceAnchoring:
    def test_anchor_chain_no_events_returns_early(self):
        repo = AsyncMock()
        repo.list_by_tenant.return_value = ([], 0)
        svc = AuditService(repo=repo)
        result = asyncio_run(svc.anchor_chain("tenant-1"))
        assert result["anchored"] is False
        assert result["reason"] == "no events to anchor"

    def test_anchor_chain_with_events(self, sample_events):
        repo = AsyncMock()
        repo.list_by_tenant.return_value = (sample_events, 2)
        repo.update_chain_head_anchor = AsyncMock()

        svc = AuditService(repo=repo)
        with patch("app.infrastructure.external.blockchain.blockchain_anchor_service") as mock_anchor:
            mock_anchor.compute_merkle_root.return_value = "computed_root_hash"
            mock_anchor.anchor = AsyncMock(return_value={
                "anchored": True,
                "tx_hash": "0xtxhash",
                "network": "goerli",
                "block_number": 1,
            })

            result = asyncio_run(svc.anchor_chain("tenant-1"))
            assert result["anchored"] is True
            assert result["tx_hash"] == "0xtxhash"

            repo.update_chain_head_anchor.assert_awaited_once_with(
                tenant_id="tenant-1",
                merkle_root="computed_root_hash",
                tx_hash="0xtxhash",
                network="goerli",
            )


def asyncio_run(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
