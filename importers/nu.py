import pandas as pd
from typing import List, Dict, Any
from core.importer import Importer
from utils.date_utils import parse_date_iso


class NUImporter(Importer):

    ACCOUNT_CODE = "NU"

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_csv(file_path)

        transactions = []

        for _, row in df.iterrows():
            try:
                date = str(row["date"]).strip()
                if not date:
                    continue

                amount = self._parse_amount(row["amount"])
                description = str(row.get("title") or "").strip()

                transactions.append({
                    "account_code": self.ACCOUNT_CODE,
                    "datetime": parse_date_iso(date),
                    "amount": amount,
                    "description": description,
                    "transaction_type_code": self._choose_type(amount),
                })

            except Exception as e:
                print(f"Error processing row: {e}")
                continue

        return transactions

    def _parse_amount(self, amount) -> float:
        if pd.isna(amount):
            return 0.0
        return -float(amount)

    def _choose_type(self, amount: float) -> str:
        return "PURCHASE" if amount < 0 else "PAYMENT"
