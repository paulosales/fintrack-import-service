from typing import Any

import pandas as pd

from core.importer import Importer
from utils.date_utils import parse_date_iso


class CIBICSavingsImporter(Importer):
    ACCOUNT_CODE = "CIBICSAV"

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        df = pd.read_csv(
            file_path, header=None, names=["date", "description", "empty", "amount"]
        )

        transactions = []

        for _, row in df.iterrows():
            try:
                date_str = str(row["date"]).strip()
                if not date_str or pd.isna(row["date"]):
                    continue

                amount = self._parse_amount(row["amount"])
                description = str(row["description"]).strip()
                type_code = self._map_type(description, amount)

                transactions.append(
                    {
                        "account_code": self.ACCOUNT_CODE,
                        "datetime": parse_date_iso(date_str),
                        "amount": amount,
                        "description": description,
                        "transaction_type_code": type_code,
                    }
                )

            except Exception as e:
                print(f"Error processing row: {e}")
                continue

        return transactions

    def _parse_amount(self, amount_str) -> float:
        if pd.isna(amount_str):
            return 0.0
        return float(amount_str)

    def _map_type(self, description: str, amount: float) -> str:
        desc = description.upper()

        if any(
            k in desc
            for k in ("BONUS INTEREST", "INTEREST", "INTERNET TRANSFER", "E-TRANSFER")
        ):
            return "PAYMENT"
        if "ELECTRONIC FUNDS TRANSFER" in desc:
            return "PURCHASE"

        return "PURCHASE" if amount < 0 else "PAYMENT"
