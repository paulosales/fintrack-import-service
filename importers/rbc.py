import pandas as pd
from typing import List, Dict, Any
from core.importer import Importer
from utils.date_utils import parse_datetime


class RBCImporter(Importer):

    ACCOUNT_CODE_MAP = {
        "Chequing": "RBCCHEK",
        "Savings": "RBCSAV",
        "Visa": "RBCVISA",
    }

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        columns = [
            "account_type",
            "account_number",
            "transaction_date",
            "cheque_number",
            "description_1",
            "description_2",
            "cad",
            "usd",
        ]
        df = pd.read_csv(file_path, names=columns, header=0, engine="python")

        transactions = []

        for _, row in df.iterrows():
            try:
                account_type = row["account_type"].strip()
                account_code = self.ACCOUNT_CODE_MAP.get(account_type)

                if not account_code:
                    print(f"Unknown account type: {account_type}")
                    continue

                datetime_str = parse_datetime(row["transaction_date"], "12:00 PM")
                amount = self._parse_amount(row)
                description = self._build_description(row)
                type_code = self._map_type(description, amount, account_type)

                transactions.append({
                    "account_code": account_code,
                    "datetime": datetime_str,
                    "amount": amount,
                    "description": description,
                    "transaction_type_code": type_code,
                })

            except Exception as e:
                print(f"Error processing row: {e}")
                continue

        return transactions

    def _parse_amount(self, row) -> float:
        cad = row.get("cad")
        usd = row.get("usd")

        if pd.notna(cad):
            return float(cad)
        if pd.notna(usd):
            return float(usd)
        return 0.0

    def _build_description(self, row) -> str:
        d1 = str(row.get("description_1") or "").strip()
        d2 = str(row.get("description_2") or "").strip()
        return " ".join(f"{d1} {d2}".split())

    def _map_type(self, description: str, amount: float, account_type: str) -> str:
        desc = description.upper()

        if "PAYROLL" in desc or "DIRECT DEP" in desc:
            return "PAYMENT"
        if "PAYMENT" in desc:
            return "PAYMENT"
        if "INTEREST" in desc:
            return "INTEREST"

        return "PURCHASE" if amount < 0 else "PAYMENT"
