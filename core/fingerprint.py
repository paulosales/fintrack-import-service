import hashlib
from typing import Dict, Any


def generate(transaction: Dict[str, Any]) -> str:
    """Generate an MD5 fingerprint for a transaction.

    The fingerprint is a deterministic hash of (datetime, amount, description)
    used for deduplication in the account-service.
    """
    raw = f"{transaction['datetime']}|{transaction['amount']}|{transaction['description']}"
    return hashlib.md5(raw.encode()).hexdigest()
