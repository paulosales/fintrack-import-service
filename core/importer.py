from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Importer(ABC):
    """Base class for all CSV importers.

    Each importer parses a CSV file and returns a list of transaction dicts
    with string-based codes (no DB IDs) so the result can be sent to Kafka
    and processed by the account-service.

    Transaction dict shape:
        {
            "account_code": str,           # e.g. "PCFINANCIAL"
            "datetime": str,               # "YYYY-MM-DD HH:MM:SS"
            "amount": float,
            "description": str,
            "transaction_type_code": str,  # e.g. "PURCHASE"
        }
    """

    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        pass
