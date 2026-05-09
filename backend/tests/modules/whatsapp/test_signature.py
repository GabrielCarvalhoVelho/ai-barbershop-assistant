from app.modules.whatsapp.signature import compute_signature, verify_signature


SECRET = "abc123secret"
BODY = b'{"object":"whatsapp_business_account","entry":[]}'


class TestComputeSignature:
    def test_returns_sha256_prefixed_hex(self):
        sig = compute_signature(BODY, SECRET)
        assert sig.startswith("sha256=")
        assert len(sig) == len("sha256=") + 64  # SHA256 hex = 64 chars

    def test_deterministic(self):
        assert compute_signature(BODY, SECRET) == compute_signature(BODY, SECRET)

    def test_changes_on_body_diff(self):
        assert compute_signature(BODY, SECRET) != compute_signature(BODY + b" ", SECRET)

    def test_changes_on_secret_diff(self):
        assert compute_signature(BODY, SECRET) != compute_signature(BODY, "outro")


class TestVerifySignature:
    def test_valid_signature_returns_true(self):
        sig = compute_signature(BODY, SECRET)
        assert verify_signature(BODY, sig, SECRET) is True

    def test_invalid_signature_returns_false(self):
        assert verify_signature(BODY, "sha256=deadbeef", SECRET) is False

    def test_missing_header_returns_false(self):
        assert verify_signature(BODY, None, SECRET) is False
        assert verify_signature(BODY, "", SECRET) is False

    def test_missing_secret_returns_false(self):
        sig = compute_signature(BODY, SECRET)
        assert verify_signature(BODY, sig, "") is False

    def test_tampered_body_returns_false(self):
        sig = compute_signature(BODY, SECRET)
        assert verify_signature(BODY + b"x", sig, SECRET) is False
