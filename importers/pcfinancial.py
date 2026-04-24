import pandas as pd
from typing import List, Dict, Any
from core.importer import Importer
from utils.date_utils import parse_datetime


class PCFinancialImporter(Importer):

    ACCOUNT_CODE = "PCFINANCIAL"

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_csv(file_path)

        transactions = []

        for _, row in df.iterrows():
            transaction_type_code = row["Type"].strip().upper()
            transactions.append({
                "account_code": self.ACCOUNT_CODE,
                "datetime": parse_datetime(row["Date"], row["Time"]),
                "amount": float(row["Amount"]),
                "description": row["Description"],
                "transaction_type_code": transaction_type_code if transaction_type_code in ("PURCHASE", "PAYMENT", "REFUND", "INTEREST") else "PURCHASE",
            })

        return transactions
