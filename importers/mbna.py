from typing import Any

import pandas as pd

from core.importer import Importer
from utils.date_utils import parse_datetime


class MBNACardImporter(Importer):
    ACCOUNT_CODE = "MBNA"

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        df = pd.read_csv(file_path)

        transactions = []

        for _, row in df.iterrows():
            try:
                date_str = row["Posted Date"]
                amount = float(row["Amount"])
                description = row["Payee"].strip()
                datetime_str = parse_datetime(date_str, "12:00 PM")
                type_code = self._map_type(description, amount)

                transactions.append(
                    {
                        "account_code": self.ACCOUNT_CODE,
                        "datetime": datetime_str,
                        "amount": amount,
                        "description": description,
                        "transaction_type_code": type_code,
                    }
                )

            except Exception as e:
                print(f"Error occurred while processing row: {e}")
                continue

        return transactions

    def _map_type(self, description: str, amount: float) -> str:
        desc = description.upper()

        if "PAYMENT" in desc:
            return "PAYMENT"
        if "REFUND" in desc:
            return "REFUND"
        if "INTEREST" in desc:
            return "INTEREST"

        return "PURCHASE" if amount < 0 else "PAYMENT"
