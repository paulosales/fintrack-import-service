import os
import sys

import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_pcfinancial_df():
    import pandas as pd

    return pd.DataFrame(
        {
            "Date": ["01/15/2024", "01/16/2024"],
            "Time": ["12:00 PM", "03:30 PM"],
            "Amount": [-50.25, 200.00],
            "Description": ["GROCERY STORE", "PAYROLL DEPOSIT"],
            "Type": ["PURCHASE", "PAYMENT"],
        }
    )


@pytest.fixture
def sample_mbna_df():
    import pandas as pd

    return pd.DataFrame(
        {
            "Posted Date": ["01/15/2024", "01/16/2024"],
            "Amount": [-75.00, 150.00],
            "Payee": ["NETFLIX SUBSCRIPTION", "PAYMENT RECEIVED"],
        }
    )


@pytest.fixture
def sample_rbc_df():
    import pandas as pd

    return pd.DataFrame(
        {
            "account_type": ["Chequing", "Chequing"],
            "account_number": ["12345", "12345"],
            "transaction_date": ["01/15/2024", "01/16/2024"],
            "cheque_number": [None, None],
            "description_1": ["TIM HORTONS", "PAYROLL"],
            "description_2": ["COFFEE", ""],
            "cad": [-5.50, 2000.00],
            "usd": [None, None],
        }
    )


@pytest.fixture
def sample_nu_df():
    import pandas as pd

    return pd.DataFrame(
        {
            "date": ["2024-01-15", "2024-01-16"],
            "amount": [50.00, -200.00],
            "title": ["Netflix", "Salary"],
        }
    )


@pytest.fixture
def sample_cibic_checking_df():
    import pandas as pd

    return pd.DataFrame(
        {
            "date": ["2024-01-15", "2024-01-16"],
            "description": ["POINT OF SALE PURCHASE", "E-TRANSFER RECEIVED"],
            "amount": [-30.00, 500.00],
            "extra": [None, None],
        }
    )


@pytest.fixture
def sample_cibic_savings_df():
    import pandas as pd

    return pd.DataFrame(
        {
            "date": ["2024-01-15", "2024-01-16"],
            "description": ["INTEREST EARNED", "ELECTRONIC FUNDS TRANSFER"],
            "empty": [None, None],
            "amount": [1.50, -100.00],
        }
    )
