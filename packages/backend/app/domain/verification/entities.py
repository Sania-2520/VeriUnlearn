import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProofType(str, Enum):
    MERKLE = "merkle"
    ZKSNARK = "zksnark"
    HYBRID = "hybrid"


class SignatureAlgorithm(str, Enum):
    ED25519 = "ed25519"


@dataclass
class DeletionProof:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    job_id: str = ""
    request_id: str = ""
    proof_type: ProofType = ProofType.MERKLE
    merkle_root: str = ""
    merkle_tree_depth: int = 0
    merkle_tree: dict = field(default_factory=dict)
    signature_algorithm: str = SignatureAlgorithm.ED25519.value
    signature_hex: str = ""
    public_key_hex: str = ""
    zk_proof: Optional[dict] = None
    certificate: Optional[str] = None
    certificate_hash: Optional[str] = None
    verified: bool = False
    verified_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class ProofVerification:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proof_id: str = ""
    verifier_id: Optional[str] = None
    verification_method: str = "api"
    is_valid: bool = False
    details: dict = field(default_factory=dict)
    verified_at: datetime = field(default_factory=datetime.utcnow)
