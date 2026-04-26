from typing import Any

import pandas as pd

from core.importer import Importer
from utils.date_utils import parse_datetime_br


class BBImporter(Importer):
    ACCOUNT_CODE = "BBCC"

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        columns = [
            "Data",
            "Lançamento",
            "Detalhes",
            "N° documento",
            "Valor",
            "Tipo Lançamento",
        ]
        df = pd.read_csv(
            file_path,
            names=columns,
            header=0,
            engine="python",
            encoding="iso-8859-1",
        )

        transactions = []

        for _, row in df.iterrows():
            try:
                date_str = row["Data"].strip()
                if date_str == "00/00/0000":
                    continue

                datetime_str = parse_datetime_br(date_str)
                amount = self._parse_amount(row["Valor"])
                description = self._build_description(row)
                type_code = self._map_type(row["Tipo Lançamento"], amount)

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
                print(f"Error processing row: {e}")
                continue

        return transactions

    def _parse_amount(self, amount_str) -> float:
        if pd.isna(amount_str):
            return 0.0
        amount_str = str(amount_str).replace(".", "").replace(",", ".")
        return float(amount_str)

    def _build_description(self, row) -> str:
        lancamento = str(row.get("Lançamento") or "").strip()
        detalhes = str(row.get("Detalhes") or "").strip()
        return " ".join(f"{lancamento} {detalhes}".split())

    def _map_type(self, tipo_lancamento, amount: float) -> str:
        tipo = str(tipo_lancamento).strip().upper()

        if tipo == "SAÍDA":
            return "PURCHASE"
        elif tipo == "ENTRADA":
            return "PAYMENT"
        return "PAYMENT"
