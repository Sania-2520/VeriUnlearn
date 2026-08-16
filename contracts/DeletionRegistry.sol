// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title DeletionRegistry
/// @notice Stores SHA-256 hashes of VeriUnlearn deletion certificates on-chain,
///         providing an immutable, third-party-verifiable anchor for GDPR/DPDP
///         erasure claims. One hash per certificate; emit events for auditability.
contract DeletionRegistry {
    mapping(bytes32 => uint256) public registeredAt;
    bytes32[] public hashes;

    event CertificateRegistered(bytes32 indexed certHash, address indexed registrar, uint256 at);

    /// @notice Register a certificate hash. Idempotent per hash.
    function register(bytes32 _hash) external {
        if (registeredAt[_hash] == 0) {
            registeredAt[_hash] = block.timestamp;
            hashes.push(_hash);
            emit CertificateRegistered(_hash, msg.sender, block.timestamp);
        }
    }

    /// @notice Total number of registered certificate hashes.
    function count() external view returns (uint256) {
        return hashes.length;
    }

    /// @notice Verify a certificate hash exists on-chain.
    function isRegistered(bytes32 _hash) external view returns (bool) {
        return registeredAt[_hash] != 0;
    }
}
