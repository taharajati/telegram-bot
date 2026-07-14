"""E2E Encryption Round-Trip Test

Tests that card info encrypted by the bot can be decrypted by the website
and vice versa, using the same ENCRYPTION_KEY.

Run:  pytest tests/test_e2e_encryption.py -v
       uv run pytest tests/test_e2e_encryption.py -v
"""
import os
import sys
import base64

# Ensure we can import bot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "telegram_order_bot"))

# ── Bot-side crypto (Python) ─────────────────────────────────────
from utils.crypto import encrypt as bot_encrypt, decrypt as bot_decrypt, safe_decrypt, safe_encrypt

# ── Website-side crypto (Node.js compatible) ─────────────────────
# We replicate the same algorithm to simulate the website's crypto.ts
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


def _website_derive_key(master_key: str) -> bytes:
    """Match crypto.ts scrypt derivation."""
    kdf = Scrypt(salt=b"foroshgram-salt", length=32, n=16384, r=8, p=1)
    return kdf.derive(master_key.encode())


def website_encrypt(plaintext: str, master_key: str) -> str:
    """Simulate encryption as done by lib/crypto.ts using Node crypto."""
    key = _website_derive_key(master_key)
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv + ct_with_tag).decode("ascii")


def website_decrypt(encrypted_b64: str, master_key: str) -> str:
    """Simulate decryption as done by lib/crypto.ts."""
    key = _website_derive_key(master_key)
    data = base64.b64decode(encrypted_b64)
    iv = data[:12]
    auth_tag = data[-16:]
    ct = data[12:-16]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ct + auth_tag, None).decode("utf-8")


# ─── Tests ────────────────────────────────────────────────────────

TEST_SAMPLES = [
    ("card_number", "6037991234567890"),         # 16-digit card
    ("card_holder", "طه رجعتی"),                   # Persian name
    ("sheba", "IR8205601234567890123456789"),     # 26-char IBAN
    ("short", "12"),                               # edge: very short
    ("long_name", "أ" * 200),                      # edge: very long
]


def test_bot_encrypt_then_decrypt():
    """Bot encrypts → bot decrypts (happy path)."""
    for label, plain in TEST_SAMPLES:
        enc = bot_encrypt(plain)
        assert enc is not None
        assert isinstance(enc, str)
        assert len(enc) > 0, f"{label}: encrypted should not be empty"
        dec = bot_decrypt(enc)
        assert dec == plain, f"{label}: round-trip failed: {dec!r} != {plain!r}"
        print(f"  ✓ {label}: {len(plain)} chars → {len(enc)} chars base64")


def test_website_encrypt_then_decrypt():
    """Website encrypts → website decrypts (happy path)."""
    master = os.environ.get("ENCRYPTION_KEY", "test-key-not-32-chars-but-ok-for-test")
    for label, plain in TEST_SAMPLES:
        enc = website_encrypt(plain, master)
        assert isinstance(enc, str) and len(enc) > 0
        dec = website_decrypt(enc, master)
        assert dec == plain, f"{label}: website round-trip failed: {dec!r} != {plain!r}"


def test_cross_platform_bot_encrypts_website_decrypts():
    """Bot encrypts → website decrypts (same master key)."""
    master = os.environ.get("ENCRYPTION_KEY", "test-key-not-32-chars-but-ok-for-test")
    os.environ["ENCRYPTION_KEY"] = master
    # Re-initialize bot module with our key (force re-derive)
    import importlib
    import utils.crypto as btc
    importlib.reload(btc)

    for label, plain in TEST_SAMPLES:
        bot_enc = btc.encrypt(plain)
        web_dec = website_decrypt(bot_enc, master)
        assert web_dec == plain, f"{label}: bot→website failed: {web_dec!r} != {plain!r}"


def test_website_encrypts_bot_decrypts():
    """Website encrypts → bot decrypts."""
    master = os.environ.get("ENCRYPTION_KEY", "test-key-not-32-chars-but-ok-for-test")
    os.environ["ENCRYPTION_KEY"] = master
    import importlib
    import utils.crypto as btc
    importlib.reload(btc)

    for label, plain in TEST_SAMPLES:
        web_enc = website_encrypt(plain, master)
        bot_dec = btc.decrypt(web_enc)
        assert bot_dec == plain, f"{label}: website→bot failed"


def test_safe_decrypt_legacy_plaintext():
    """safe_decrypt on already-plaintext data returns as-is (backward compat)."""
    assert safe_decrypt("6037991234567890") == "6037991234567890"
    assert safe_decrypt(None) is None


def test_safe_encrypt_twice_different():
    """Encrypting the same plaintext twice gives different ciphertext (random IV)."""
    plain = "6037991234567890"
    e1 = safe_encrypt(plain)
    e2 = safe_encrypt(plain)
    assert e1 != e2, "encryption should be non-deterministic (different IV each time)"


def test_encrypted_output_length():
    """Verify base64 output length for typical inputs."""
    card = "6037991234567890"  # 16 bytes plaintext
    name = "طه رجعتی"            # ~10 bytes (UTF-8 Persian)
    iban = "IR8205601234567890123456789"  # 26 bytes

    for label, plain in [("card", card), ("name", name), ("iban", iban)]:
        enc = bot_encrypt(plain)
        decoded = base64.b64decode(enc)
        iv = 12
        auth_tag = 16
        ct_len = len(decoded) - iv - auth_tag
        print(f"  {label}: {len(plain)}B plain → {len(enc)} chars base64 ({ct_len}B ciphertext)")
        assert len(enc) >= 40, f"{label}: output too short ({len(enc)})"


def test_wrong_key_fails():
    """Decrypting with a different key should fail."""
    plain = "6037991234567890"
    enc = bot_encrypt(plain)
    # Temporarily change key
    old_key = os.environ.get("ENCRYPTION_KEY", "")
    os.environ["ENCRYPTION_KEY"] = "a" * 40  # different key
    import importlib
    import utils.crypto as btc
    importlib.reload(btc)
    try:
        result = btc.decrypt(enc)
        assert result != plain, "decrypt with wrong key should return garbage or raise"
    except Exception:
        pass  # expected
    finally:
        os.environ["ENCRYPTION_KEY"] = old_key
        importlib.reload(btc)
