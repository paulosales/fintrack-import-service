import pandas as pd
from typing import List, Dict, Any
from core.importer import Importer
from utils.date_utils import parse_datetime_br


class C6CheckingImporter(Importer):
    """
    Importer for C6 Bank Conta Corrente CSV export.

    Expected header row (after variable metadata lines):
        Data Lançamento,Data Contábil,Título,Descrição,Entrada(R$),Saída(R$),Saldo do Dia(R$)

    Amount convention:
        - Entrada (credit/income) → positive amount
        - Saída   (debit/expense) → negative amount
    """

    ACCOUNT_CODE = "C6CHECK"
    HEADER_ROW = "Data Lançamento"

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        header_line = self._find_header_line(file_path)

        df = pd.read_csv(file_path, skiprows=header_line, encoding="utf-8")
        df.columns = [c.strip() for c in df.columns]

        transactions = []

        for _, row in df.iterrows():
            try:
                date_str = str(row["Data Lançamento"]).strip()
                if not date_str or pd.isna(row["Data Lançamento"]):
                    continue

                credit = self._parse_brl(row["Entrada(R$)"])
                debit = self._parse_brl(row["Saída(R$)"])

                if credit == 0.0 and debit == 0.0:
                    continue

                amount = credit - debit
                title = str(row.get("Título", "") or "").strip()
                description = str(row.get("Descrição", "") or "").strip()
                full_description = self._build_description(title, description)
                type_code = self._map_type(full_description, amount)

                transactions.append({
                    "account_code": self.ACCOUNT_CODE,
                    "datetime": parse_datetime_br(date_str),
                    "amount": amount,
                    "description": full_description,
                    "transaction_type_code": type_code,
                })

            except Exception as e:
                print(f"[C6Checking] Error processing row: {e}")
                continue

        return transactions

    def _find_header_line(self, file_path: str) -> int:
        with open(file_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if line.startswith(self.HEADER_ROW):
                    return i
        return 0

    def _parse_brl(self, value) -> float:
        if pd.isna(value):
            return 0.0
        try:
            return float(str(value).replace(".", "").replace(",", "."))
        except (ValueError, AttributeError):
            return 0.0

    def _build_description(self, title: str, description: str) -> str:
        parts = [p for p in [title, description] if p]
        return " - ".join(parts) if parts else ""

    def _map_type(self, description: str, amount: float) -> str:
        desc = description.upper()

        if "PAGAMENTO" in desc or "PAYMENT" in desc:
            return "PAYMENT"
        if "JUROS" in desc or "INTEREST" in desc:
            return "INTEREST"
        if "ESTORNO" in desc or "REFUND" in desc:
            return "REFUND"

        return "PURCHASE" if amount < 0 else "PAYMENT"
