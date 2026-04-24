import pytest
from unittest.mock import patch
from importers.pcfinancial import PCFinancialImporter
from importers.mbna import MBNACardImporter
from importers.rbc import RBCImporter
from importers.nu import NUImporter
from importers.cibic_checking import CIBICCheckingImporter
from importers.cibic_savings import CIBICSavingsImporter
from importers.bb import BBImporter


class TestPCFinancialImporter:

    def test_parse_returns_correct_fields(self, sample_pcfinancial_df):
        with patch("pandas.read_csv", return_value=sample_pcfinancial_df):
            result = PCFinancialImporter().parse("dummy.csv")

        assert len(result) == 2
        for t in result:
            assert "account_code" in t
            assert "datetime" in t
            assert "amount" in t
            assert "description" in t
            assert "transaction_type_code" in t

    def test_parse_account_code(self, sample_pcfinancial_df):
        with patch("pandas.read_csv", return_value=sample_pcfinancial_df):
            result = PCFinancialImporter().parse("dummy.csv")

        assert all(t["account_code"] == "PCFINANCIAL" for t in result)

    def test_parse_purchase_type(self, sample_pcfinancial_df):
        with patch("pandas.read_csv", return_value=sample_pcfinancial_df):
            result = PCFinancialImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PURCHASE"
        assert result[0]["amount"] == -50.25

    def test_parse_payment_type(self, sample_pcfinancial_df):
        with patch("pandas.read_csv", return_value=sample_pcfinancial_df):
            result = PCFinancialImporter().parse("dummy.csv")

        assert result[1]["transaction_type_code"] == "PAYMENT"
        assert result[1]["amount"] == 200.00

    def test_parse_datetime_format(self, sample_pcfinancial_df):
        with patch("pandas.read_csv", return_value=sample_pcfinancial_df):
            result = PCFinancialImporter().parse("dummy.csv")

        assert result[0]["datetime"] == "2024-01-15 12:00:00"
        assert result[1]["datetime"] == "2024-01-16 15:30:00"

    def test_unknown_type_defaults_to_purchase(self):
        import pandas as pd
        df = pd.DataFrame({
            "Date": ["01/15/2024"],
            "Time": ["12:00 PM"],
            "Amount": [-10.00],
            "Description": ["Mystery charge"],
            "Type": ["UNKNOWN_TYPE"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = PCFinancialImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PURCHASE"


class TestMBNACardImporter:

    def test_parse_returns_correct_fields(self, sample_mbna_df):
        with patch("pandas.read_csv", return_value=sample_mbna_df):
            result = MBNACardImporter().parse("dummy.csv")

        assert len(result) == 2
        for t in result:
            assert t["account_code"] == "MBNA"
            assert "datetime" in t
            assert "amount" in t

    def test_payment_keyword_maps_to_payment(self):
        import pandas as pd
        df = pd.DataFrame({
            "Posted Date": ["01/15/2024"],
            "Amount": [100.00],
            "Payee": ["PAYMENT RECEIVED"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = MBNACardImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PAYMENT"

    def test_refund_keyword_maps_to_refund(self):
        import pandas as pd
        df = pd.DataFrame({
            "Posted Date": ["01/15/2024"],
            "Amount": [25.00],
            "Payee": ["AMAZON REFUND"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = MBNACardImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "REFUND"

    def test_interest_keyword_maps_to_interest(self):
        import pandas as pd
        df = pd.DataFrame({
            "Posted Date": ["01/15/2024"],
            "Amount": [5.00],
            "Payee": ["INTEREST CHARGE"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = MBNACardImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "INTEREST"

    def test_negative_amount_defaults_to_purchase(self):
        import pandas as pd
        df = pd.DataFrame({
            "Posted Date": ["01/15/2024"],
            "Amount": [-30.00],
            "Payee": ["COFFEE SHOP"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = MBNACardImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PURCHASE"


class TestRBCImporter:

    def test_parse_chequing_account_code(self, sample_rbc_df):
        with patch("pandas.read_csv", return_value=sample_rbc_df):
            result = RBCImporter().parse("dummy.csv")

        assert all(t["account_code"] == "RBCCHEK" for t in result)

    def test_parse_unknown_account_type_is_skipped(self):
        import pandas as pd
        df = pd.DataFrame({
            "account_type": ["Unknown"],
            "account_number": ["999"],
            "transaction_date": ["01/15/2024"],
            "cheque_number": [None],
            "description_1": ["desc"],
            "description_2": [""],
            "cad": [-10.00],
            "usd": [None],
        })
        with patch("pandas.read_csv", return_value=df):
            result = RBCImporter().parse("dummy.csv")

        assert result == []

    def test_savings_account_maps_correctly(self):
        import pandas as pd
        df = pd.DataFrame({
            "account_type": ["Savings"],
            "account_number": ["99999"],
            "transaction_date": ["01/15/2024"],
            "cheque_number": [None],
            "description_1": ["DEPOSIT"],
            "description_2": [""],
            "cad": [500.00],
            "usd": [None],
        })
        with patch("pandas.read_csv", return_value=df):
            result = RBCImporter().parse("dummy.csv")

        assert result[0]["account_code"] == "RBCSAV"

    def test_visa_account_maps_correctly(self):
        import pandas as pd
        df = pd.DataFrame({
            "account_type": ["Visa"],
            "account_number": ["4111"],
            "transaction_date": ["01/15/2024"],
            "cheque_number": [None],
            "description_1": ["PURCHASE"],
            "description_2": [""],
            "cad": [-100.00],
            "usd": [None],
        })
        with patch("pandas.read_csv", return_value=df):
            result = RBCImporter().parse("dummy.csv")

        assert result[0]["account_code"] == "RBCVISA"


class TestNUImporter:

    def test_parse_account_code(self, sample_nu_df):
        with patch("pandas.read_csv", return_value=sample_nu_df):
            result = NUImporter().parse("dummy.csv")

        assert all(t["account_code"] == "NU" for t in result)

    def test_positive_input_amount_becomes_negative(self, sample_nu_df):
        """NU CSVs use positive values for expenses; importer negates them."""
        with patch("pandas.read_csv", return_value=sample_nu_df):
            result = NUImporter().parse("dummy.csv")

        # 50.00 input → -50.00, type PURCHASE
        assert result[0]["amount"] == -50.00
        assert result[0]["transaction_type_code"] == "PURCHASE"

    def test_negative_input_amount_becomes_positive(self, sample_nu_df):
        """Negative NU amount (e.g. refund) becomes positive → PAYMENT."""
        with patch("pandas.read_csv", return_value=sample_nu_df):
            result = NUImporter().parse("dummy.csv")

        # -200.00 input → 200.00, type PAYMENT
        assert result[1]["amount"] == 200.00
        assert result[1]["transaction_type_code"] == "PAYMENT"

    def test_uses_title_as_description(self, sample_nu_df):
        with patch("pandas.read_csv", return_value=sample_nu_df):
            result = NUImporter().parse("dummy.csv")

        assert result[0]["description"] == "Netflix"
        assert result[1]["description"] == "Salary"


class TestCIBICCheckingImporter:

    def test_parse_account_code(self, sample_cibic_checking_df):
        with patch("pandas.read_csv", return_value=sample_cibic_checking_df):
            result = CIBICCheckingImporter().parse("dummy.csv")

        assert all(t["account_code"] == "CIBICCHK" for t in result)

    def test_point_of_sale_maps_to_purchase(self, sample_cibic_checking_df):
        with patch("pandas.read_csv", return_value=sample_cibic_checking_df):
            result = CIBICCheckingImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PURCHASE"

    def test_etransfer_maps_to_payment(self, sample_cibic_checking_df):
        with patch("pandas.read_csv", return_value=sample_cibic_checking_df):
            result = CIBICCheckingImporter().parse("dummy.csv")

        assert result[1]["transaction_type_code"] == "PAYMENT"


class TestCIBICSavingsImporter:

    def test_parse_account_code(self, sample_cibic_savings_df):
        with patch("pandas.read_csv", return_value=sample_cibic_savings_df):
            result = CIBICSavingsImporter().parse("dummy.csv")

        assert all(t["account_code"] == "CIBICSAV" for t in result)

    def test_interest_maps_to_payment(self, sample_cibic_savings_df):
        with patch("pandas.read_csv", return_value=sample_cibic_savings_df):
            result = CIBICSavingsImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PAYMENT"

    def test_eft_maps_to_purchase(self, sample_cibic_savings_df):
        with patch("pandas.read_csv", return_value=sample_cibic_savings_df):
            result = CIBICSavingsImporter().parse("dummy.csv")

        assert result[1]["transaction_type_code"] == "PURCHASE"


class TestBBImporter:

    def test_parse_account_code(self):
        import pandas as pd
        df = pd.DataFrame({
            "Data": ["15/01/2024"],
            "Lançamento": ["PIX ENVIADO"],
            "Detalhes": ["Mercado"],
            "N° documento": ["123"],
            "Valor": ["-150,00"],
            "Tipo Lançamento": ["SAÍDA"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = BBImporter().parse("dummy.csv")

        assert result[0]["account_code"] == "BBCC"

    def test_saida_maps_to_purchase(self):
        import pandas as pd
        df = pd.DataFrame({
            "Data": ["15/01/2024"],
            "Lançamento": ["PIX ENVIADO"],
            "Detalhes": [""],
            "N° documento": ["123"],
            "Valor": ["-200,00"],
            "Tipo Lançamento": ["SAÍDA"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = BBImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PURCHASE"

    def test_entrada_maps_to_payment(self):
        import pandas as pd
        df = pd.DataFrame({
            "Data": ["15/01/2024"],
            "Lançamento": ["SALARIO"],
            "Detalhes": ["Empresa"],
            "N° documento": ["456"],
            "Valor": ["3000,00"],
            "Tipo Lançamento": ["ENTRADA"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = BBImporter().parse("dummy.csv")

        assert result[0]["transaction_type_code"] == "PAYMENT"

    def test_summary_row_is_skipped(self):
        import pandas as pd
        df = pd.DataFrame({
            "Data": ["00/00/0000"],
            "Lançamento": ["SALDO"],
            "Detalhes": [""],
            "N° documento": [""],
            "Valor": ["1000,00"],
            "Tipo Lançamento": ["ENTRADA"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = BBImporter().parse("dummy.csv")

        assert result == []

    def test_brl_amount_parsing(self):
        import pandas as pd
        df = pd.DataFrame({
            "Data": ["15/01/2024"],
            "Lançamento": ["Compra"],
            "Detalhes": [""],
            "N° documento": ["1"],
            "Valor": ["-1.234,56"],
            "Tipo Lançamento": ["SAÍDA"],
        })
        with patch("pandas.read_csv", return_value=df):
            result = BBImporter().parse("dummy.csv")

        assert result[0]["amount"] == pytest.approx(-1234.56)
