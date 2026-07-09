import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BlockchainTransaction:
    def __init__(
        self,
        tx_hash: str,
        merkle_root: str,
        tenant_id: str,
        network: str,
        block_number: int = 0,
        status: str = "confirmed",
    ) -> None:
        self.tx_hash = tx_hash
        self.merkle_root = merkle_root
        self.tenant_id = tenant_id
        self.network = network
        self.block_number = block_number
        self.status = status
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "merkle_root": self.merkle_root,
            "tenant_id": self.tenant_id,
            "network": self.network,
            "block_number": self.block_number,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }


class SimulatedBlockchain:
    """In-memory simulated blockchain for development."""

    def __init__(self) -> None:
        self._blocks: list[dict[str, Any]] = []
        self._ledger: dict[str, BlockchainTransaction] = {}
        self._block_counter = 0

    def submit_root(self, merkle_root: str, tenant_id: str, network: str) -> BlockchainTransaction:
        self._block_counter += 1
        raw = f"{merkle_root}:{tenant_id}:{network}:{self._block_counter}:{datetime.now(timezone.utc).isoformat()}"
        tx_hash = hashlib.sha256(raw.encode()).hexdigest()

        tx = BlockchainTransaction(
            tx_hash=tx_hash,
            merkle_root=merkle_root,
            tenant_id=tenant_id,
            network=network,
            block_number=self._block_counter,
        )
        self._ledger[tx_hash] = tx

        block = {
            "block_number": self._block_counter,
            "transactions": [tx.to_dict()],
            "previous_block_hash": self._blocks[-1]["block_hash"] if self._blocks else "0" * 64,
        }
        block["block_hash"] = hashlib.sha256(
            json.dumps(block, sort_keys=True, default=str).encode()
        ).hexdigest()
        self._blocks.append(block)

        logger.info(
            "Simulated blockchain: anchored root %s in block %d (tx=%s)",
            merkle_root[:16], self._block_counter, tx_hash[:16],
        )
        return tx

    def get_transaction(self, tx_hash: str) -> Optional[BlockchainTransaction]:
        return self._ledger.get(tx_hash)

    def verify_root(self, merkle_root: str, tx_hash: str) -> bool:
        tx = self._ledger.get(tx_hash)
        if not tx:
            return False
        return tx.merkle_root == merkle_root and tx.status == "confirmed"

    def get_chain_height(self) -> int:
        return self._block_counter


class BlockchainAnchoringService:
    def __init__(self) -> None:
        self._simulated = SimulatedBlockchain()
        self._network = settings.audit_blockchain_network
        self._enabled = settings.audit_blockchain_anchoring

    async def anchor(
        self,
        merkle_root: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        if not self._enabled:
            return {
                "anchored": False,
                "tx_hash": None,
                "network": self._network,
                "reason": "blockchain anchoring disabled",
            }

        tx = self._simulated.submit_root(
            merkle_root=merkle_root,
            tenant_id=tenant_id,
            network=self._network,
        )

        return {
            "anchored": True,
            "tx_hash": tx.tx_hash,
            "network": tx.network,
            "block_number": tx.block_number,
            "timestamp": tx.timestamp.isoformat(),
            "status": tx.status,
        }

    async def verify(
        self,
        merkle_root: str,
        tx_hash: str,
    ) -> dict[str, Any]:
        is_valid = self._simulated.verify_root(merkle_root, tx_hash)
        tx = self._simulated.get_transaction(tx_hash)

        return {
            "is_valid": is_valid,
            "tx_hash": tx_hash,
            "merkle_root": merkle_root,
            "network": tx.network if tx else self._network,
            "block_number": tx.block_number if tx else None,
            "anchored_at": tx.timestamp.isoformat() if tx else None,
        }

    async def get_transaction(self, tx_hash: str) -> Optional[dict[str, Any]]:
        tx = self._simulated.get_transaction(tx_hash)
        return tx.to_dict() if tx else None

    async def is_anchored(self, tx_hash: str) -> bool:
        return self._simulated.get_transaction(tx_hash) is not None

    def compute_merkle_root(self, events: list[dict[str, Any]]) -> str:
        if not events:
            return hashlib.sha256(b"empty").hexdigest()

        event_hashes = []
        for ev in events:
            data = json.dumps(ev, sort_keys=True, default=str).encode()
            event_hashes.append(hashlib.sha256(data).hexdigest())

        while len(event_hashes) > 1:
            next_level = []
            for i in range(0, len(event_hashes), 2):
                if i + 1 < len(event_hashes):
                    combined = event_hashes[i] + event_hashes[i + 1]
                else:
                    combined = event_hashes[i] + event_hashes[i]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            event_hashes = next_level

        return event_hashes[0]


blockchain_anchor_service = BlockchainAnchoringService()
