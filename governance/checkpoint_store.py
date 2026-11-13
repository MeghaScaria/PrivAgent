"""
Persistent, local storage for the human-approval workflow: LangGraph
checkpoints (SQLite), the execution ledger, and the key that signs
approvals. For development and single-machine use only: one SQLite file
per store, no multi-worker coordination, no key rotation.

Everything lives in one directory (DEFAULT_DIR unless given):
  checkpoints.sqlite  LangGraph checkpoints (paused runs)
  ledger.sqlite       ExecutionLedger (at-most-once execution)
  master.key          32 random bytes; approval and checkpoint keys are
                      derived from it. PRIVAGENT_MASTER_KEY (64 hex
                      chars) overrides the file, e.g. from a secret store.

Protections:
  - The directory and files are private to the current user: mode
    0700/0600 on POSIX; on Windows inheritance is removed and only the
    current user is granted access (icacls). check_private() reports
    anything broader.
  - Checkpoint deserialization is strict, following the LangGraph
    serializer's security note: no pickle fallback and only the
    library's built-in safe msgpack types (allowed_msgpack_modules=None),
    so a tampered database can't make it construct arbitrary objects.
  - Every checkpoint blob is encrypted with AES-GCM under a key derived
    from the master key. Blobs that aren't encrypted, or that fail
    authentication, are refused rather than read.
  - The approval graph drops raw documents, records and the analysis
    from state before anything is checkpointed (see agents/approval_flow.py),
    and completed threads are deleted, so what's stored is the minimum
    needed to resume a paused review, encrypted.
"""
import getpass
import hashlib
import hmac
import os
import secrets
import sqlite3
import subprocess
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from langgraph.checkpoint.serde.base import CipherProtocol
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

from governance.approval import ApprovalService, ExecutionLedger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(BASE_DIR, "runtime", "approvals")
CHECKPOINT_DB = "checkpoints.sqlite"
LEDGER_DB = "ledger.sqlite"
MASTER_KEY_FILE = "master.key"
MASTER_KEY_ENV = "PRIVAGENT_MASTER_KEY"
CIPHER_NAME = "aesgcm"
_AAD = b"privagent-checkpoint-v1"
_BROAD_PRINCIPALS = ("Everyone", "BUILTIN\\Users", "Authenticated Users", "NT AUTHORITY\\Authenticated")


# -- access control ------------------------------------------------------

def _windows_owner_only(path, is_dir):
    user = os.environ.get("USERDOMAIN", "") + "\\" + getpass.getuser() \
        if os.environ.get("USERDOMAIN") else getpass.getuser()
    grant = f"{user}:(OI)(CI)F" if is_dir else f"{user}:F"
    subprocess.run(["icacls", path, "/inheritance:r", "/grant:r", grant],
                   check=True, capture_output=True)


def make_private(path):
    """Restricts a file or directory to the current user."""
    is_dir = os.path.isdir(path)
    if sys.platform == "win32":
        _windows_owner_only(path, is_dir)
    else:
        os.chmod(path, 0o700 if is_dir else 0o600)


def check_private(path):
    """Problems with a path's access control; an empty list means it's
    private to the current user."""
    if sys.platform == "win32":
        out = subprocess.run(["icacls", path], capture_output=True, text=True).stdout
        problems = [p for p in _BROAD_PRINCIPALS if p.lower() in out.lower()]
        if "(I)" in out:
            problems.append("inherits permissions from its parent")
        return problems
    mode = os.stat(path).st_mode & 0o777
    return [f"mode {oct(mode)} allows group/other access"] if mode & 0o077 else []


def _private_dir(path):
    os.makedirs(path, exist_ok=True)
    make_private(path)
    return path


def _private_file(path, create):
    if not os.path.exists(path):
        create(path)
    make_private(path)
    return path


# -- keys ----------------------------------------------------------------

def load_master_key(directory):
    from_env = os.environ.get(MASTER_KEY_ENV)
    if from_env:
        key = bytes.fromhex(from_env)
        if len(key) != 32:
            raise ValueError(f"{MASTER_KEY_ENV} must be 32 bytes (64 hex characters)")
        return key
    path = os.path.join(directory, MASTER_KEY_FILE)

    def create(p):
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(32))
    _private_file(path, create)
    with open(path, "rb") as f:
        key = f.read()
    if len(key) != 32:
        raise ValueError(f"{path} is not a valid 32-byte key")
    return key


def derive_key(master, purpose):
    return hmac.new(master, purpose.encode("utf-8"), hashlib.sha256).digest()


# -- serializer ----------------------------------------------------------

class AesGcmCipher(CipherProtocol):
    def __init__(self, key):
        self._aead = AESGCM(key)

    def encrypt(self, plaintext):
        nonce = secrets.token_bytes(12)
        return CIPHER_NAME, nonce + self._aead.encrypt(nonce, plaintext, _AAD)

    def decrypt(self, ciphername, ciphertext):
        if ciphername != CIPHER_NAME:
            raise ValueError(f"Unsupported checkpoint cipher: {ciphername!r}")
        return self._aead.decrypt(ciphertext[:12], ciphertext[12:], _AAD)


class StrictEncryptedSerializer(EncryptedSerializer):
    """EncryptedSerializer that refuses unencrypted blobs. The base class
    reads them as plaintext, which would let anyone who can write to the
    database skip the encryption."""

    def loads_typed(self, data):
        typ, _ = data
        if not typ.endswith("+" + CIPHER_NAME):
            raise ValueError(f"Refusing unencrypted checkpoint data (type {typ!r})")
        return super().loads_typed(data)


def strict_serializer(key):
    serde = JsonPlusSerializer(pickle_fallback=False, allowed_json_modules=None,
                               allowed_msgpack_modules=None)
    return StrictEncryptedSerializer(AesGcmCipher(key), serde)


# -- store ---------------------------------------------------------------

class DevApprovalStore:
    """The checkpointer, ledger and approval service for one store
    directory. Every process that opens the same directory sees the
    same paused runs and can resume them."""

    def __init__(self, directory=None, flow_rules=()):
        self.directory = _private_dir(directory or DEFAULT_DIR)
        master = load_master_key(self.directory)
        self.checkpoint_path = os.path.join(self.directory, CHECKPOINT_DB)
        self.ledger_path = os.path.join(self.directory, LEDGER_DB)

        self._conn = sqlite3.connect(self.checkpoint_path, check_same_thread=False)
        make_private(self.checkpoint_path)
        self.checkpointer = SqliteSaver(self._conn, serde=strict_serializer(
            derive_key(master, "checkpoint-aes-gcm")))
        self.checkpointer.setup()

        self.ledger = ExecutionLedger(self.ledger_path)
        make_private(self.ledger_path)
        self.service = ApprovalService(self.ledger, flow_rules=flow_rules,
                                       key=derive_key(master, "approval-service"),
                                       purge_completed=True)

    def access_problems(self):
        return {p: check_private(p) for p in (self.directory, self.checkpoint_path,
                                              self.ledger_path)}

    def close(self):
        self._conn.close()
