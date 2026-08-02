import pytest

from verification.signatures import SignatureManager


class TestSignatureManager:
    def setup_method(self):
        self.sig_manager = SignatureManager(algorithm="ed25519")

    def test_key_generation(self):
        private_key, public_key = self.sig_manager.generate_key_pair()
        assert private_key is not None
        assert public_key is not None

    def test_sign_and_verify(self):
        private_key, public_key = self.sig_manager.generate_key_pair()
        message = "test_message_to_sign"
        signature = self.sig_manager.sign(message, private_key)
        assert signature is not None
        assert len(signature) > 0

        is_valid = self.sig_manager.verify(message, signature, public_key)
        assert is_valid

    def test_verify_rejects_tampered_message(self):
        private_key, public_key = self.sig_manager.generate_key_pair()
        message = "original_message"
        signature = self.sig_manager.sign(message, private_key)

        is_valid = self.sig_manager.verify(
            "tampered_message", signature, public_key
        )
        assert not is_valid

    def test_verify_rejects_wrong_key(self):
        private_key, public_key = self.sig_manager.generate_key_pair()
        wrong_private_key, wrong_public_key = self.sig_manager.generate_key_pair()
        message = "test_message"
        signature = self.sig_manager.sign(message, private_key)

        is_valid = self.sig_manager.verify(message, signature, wrong_public_key)
        assert not is_valid

    def test_serialize_and_load_public_key(self):
        private_key, public_key = self.sig_manager.generate_key_pair()
        pem = self.sig_manager.serialize_public_key(public_key)
        assert pem.startswith("-----BEGIN PUBLIC KEY-----")

        loaded_key = self.sig_manager.load_public_key(pem)
        message = "test"
        signature = self.sig_manager.sign(message, private_key)
        assert self.sig_manager.verify(message, signature, loaded_key)

    def test_different_messages_different_signatures(self):
        private_key, public_key = self.sig_manager.generate_key_pair()
        sig1 = self.sig_manager.sign("message1", private_key)
        sig2 = self.sig_manager.sign("message2", private_key)
        assert sig1 != sig2

    def test_rsa_algorithm(self):
        rsa_manager = SignatureManager(algorithm="rsa")
        private_key, public_key = rsa_manager.generate_key_pair()
        message = "test_rsa_message"
        signature = rsa_manager.sign(message, private_key)
        assert rsa_manager.verify(message, signature, public_key)
