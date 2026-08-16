"""Blockchain-backed certificate registration.

Two modes, same interface:

- **local ledger (default)** — certificate hashes are persisted in
  ``blockchain_ledger`` forming an immutable, queryable record. This is the
  zero-infrastructure mode used by the vertical slice.
- **Ethereum testnet (optional)** — when ``BLOCKCHAIN_ENABLED`` and
  ``BLOCKCHAIN_RPC_URL`` are configured, the certificate hash is submitted to a
  registry contract via ``web3.py`` (see ``contracts/DeletionRegistry.sol``).

``web3`` is an optional dependency; the service degrades gracefully to the
local ledger with an explicit log when it is missing.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import BlockchainLedger

logger = logging.getLogger("veriunlearn.blockchain")


class BlockchainService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_certificate(self, certificate_id: str, cert_hash: str) -> dict[str, Any]:
        tx_hash: str | None = None
        chain = "local"
        status = "recorded"

        if settings.BLOCKCHAIN_ENABLED and settings.BLOCKCHAIN_RPC_URL:
            try:
                tx_hash = self._submit_to_chain(certificate_id, cert_hash)
                chain = "ethereum-testnet"
                status = "submitted"
            except Exception as exc:  # noqa: BLE001 - never fail a deletion for chain issues
                logger.warning("Blockchain submission failed, falling back to local ledger: %s", exc)

        entry = BlockchainLedger(
            certificate_id=certificate_id,
            cert_hash=cert_hash,
            chain=chain,
            tx_hash=tx_hash,
            status=status,
        )
        self.session.add(entry)
        await self.session.flush()
        return {
            "certificate_id": certificate_id,
            "cert_hash": cert_hash,
            "chain": chain,
            "tx_hash": tx_hash,
            "status": status,
        }

    def _submit_to_chain(self, certificate_id: str, cert_hash: str) -> str:
        """Submit the certificate hash to the registry contract.

        Requires the optional ``web3`` package and a funded account. The
        registry ABI is minimal (``register(bytes32 _hash)``) — see
        ``contracts/DeletionRegistry.sol``. Throws on any failure so the caller
        can fall back to the local ledger.
        """
        try:
            from web3 import Web3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("web3 not installed (pip install web3)") from exc

        w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))
        if not w3.is_connected():
            raise RuntimeError("Cannot connect to blockchain RPC")
        if not settings.BLOCKCHAIN_REGISTRY_ADDRESS:
            raise RuntimeError("BLOCKCHAIN_REGISTRY_ADDRESS not configured")

        registry_abi = [
            {
                "constant": False,
                "inputs": [{"name": "_hash", "type": "bytes32"}],
                "name": "register",
                "outputs": [],
                "type": "function",
            }
        ]
        registry = w3.eth.contract(address=settings.BLOCKCHAIN_REGISTRY_ADDRESS, abi=registry_abi)
        account = w3.eth.default_account or w3.eth.accounts[0]
        tx = registry.functions.register(bytes.fromhex(cert_hash)).build_transaction(
            {"from": account, "nonce": w3.eth.get_transaction_count(account)}
        )
        signed = w3.eth.account.sign_transaction(tx, private_key=settings.BLOCKCHAIN_PRIVATE_KEY)  # type: ignore[attr-defined]
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        return w3.to_hex(tx_hash)
