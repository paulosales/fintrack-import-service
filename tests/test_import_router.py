import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH_HEADER = {"Authorization": "Bearer test-token"}

MINIMAL_CSV = (
    b"Date,Time,Amount,Description,Type\n01/15/2024,12:00 PM,-50.00,Coffee,PURCHASE\n"
)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestImportEndpoint:
    def _upload(
        self,
        importer_type: str,
        content: bytes = MINIMAL_CSV,
        token: str = "test-token",
    ):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return client.post(
            f"/api/v1/import/{importer_type}",
            files={"file": ("transactions.csv", io.BytesIO(content), "text/csv")},
            headers=headers,
        )

    def test_missing_auth_returns_401(self):
        response = client.post(
            "/api/v1/import/pcfinancial",
            files={"file": ("t.csv", io.BytesIO(MINIMAL_CSV), "text/csv")},
        )
        assert response.status_code == 401

    def test_unknown_importer_returns_400(self):
        response = self._upload("unknown-bank")
        assert response.status_code == 400
        assert "Unknown importer" in response.json()["detail"]

    def test_successful_import_queues_transactions(self):
        mock_transactions = [
            {
                "account_code": "PCFINANCIAL",
                "datetime": "2024-01-15 12:00:00",
                "amount": -50.00,
                "description": "Coffee",
                "transaction_type_code": "PURCHASE",
            }
        ]
        with (
            patch("routers.import_router.PCFinancialImporter") as MockImporter,
            patch(
                "routers.import_router.publish_import_batch", return_value="abc-123"
            ) as mock_pub,
        ):
            MockImporter.return_value.parse.return_value = mock_transactions
            response = self._upload("pcfinancial")

        assert response.status_code == 200
        body = response.json()
        assert body["import_id"] == "abc-123"
        assert body["queued_count"] == 1
        assert body["importer"] == "pcfinancial"
        mock_pub.assert_called_once()

    def test_empty_file_returns_400(self):
        with (
            patch("routers.import_router.PCFinancialImporter") as MockImporter,
        ):
            MockImporter.return_value.parse.return_value = []
            response = self._upload("pcfinancial", content=b"")

        assert response.status_code == 400

    def test_importer_parse_error_returns_422(self):
        MockImporterClass = MagicMock()
        MockImporterClass.return_value.parse.side_effect = Exception("bad CSV")
        with patch.dict(
            "routers.import_router.IMPORTERS", {"pcfinancial": MockImporterClass}
        ):
            response = self._upload("pcfinancial")

        assert response.status_code == 422
        assert "Failed to parse CSV" in response.json()["detail"]

    def test_kafka_publish_error_returns_503(self):
        mock_transactions = [
            {
                "account_code": "PCFINANCIAL",
                "datetime": "2024-01-15 12:00:00",
                "amount": -50.00,
                "description": "Coffee",
                "transaction_type_code": "PURCHASE",
            }
        ]
        with (
            patch("routers.import_router.PCFinancialImporter") as MockImporter,
            patch(
                "routers.import_router.publish_import_batch",
                side_effect=Exception("RabbitMQ down"),
            ),
        ):
            MockImporter.return_value.parse.return_value = mock_transactions
            response = self._upload("pcfinancial")

        assert response.status_code == 503

    def test_all_importer_types_are_accepted(self):
        importers = [
            "pcfinancial",
            "mbna",
            "rbc",
            "bb",
            "nu",
            "cibic-checking",
            "cibic-savings",
            "c6-checking",
        ]
        mock_transactions = [
            {
                "account_code": "TEST",
                "datetime": "2024-01-15 12:00:00",
                "amount": -10.00,
                "description": "Test",
                "transaction_type_code": "PURCHASE",
            }
        ]
        for imp in importers:
            MockImporterClass = MagicMock()
            MockImporterClass.return_value.parse.return_value = mock_transactions
            with (
                patch.dict("routers.import_router.IMPORTERS", {imp: MockImporterClass}),
                patch("routers.import_router.publish_import_batch", return_value="x"),
            ):
                response = self._upload(imp)

            assert response.status_code == 200, f"Failed for importer: {imp}"

    def test_fingerprint_added_to_transactions(self):
        mock_transactions = [
            {
                "account_code": "PCFINANCIAL",
                "datetime": "2024-01-15 12:00:00",
                "amount": -50.00,
                "description": "Coffee",
                "transaction_type_code": "PURCHASE",
            }
        ]
        captured = {}

        def capture_publish(importer_type, transactions):
            captured["transactions"] = transactions
            return "test-id"

        with (
            patch("routers.import_router.PCFinancialImporter") as MockImporter,
            patch(
                "routers.import_router.publish_import_batch",
                side_effect=capture_publish,
            ),
        ):
            MockImporter.return_value.parse.return_value = mock_transactions
            response = self._upload("pcfinancial")

        assert response.status_code == 200
        assert "fingerprint" in captured["transactions"][0]
        assert captured["transactions"][0]["fingerprint"] != ""
