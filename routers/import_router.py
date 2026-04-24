import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.fingerprint import generate
from importers.pcfinancial import PCFinancialImporter
from importers.mbna import MBNACardImporter
from importers.rbc import RBCImporter
from importers.bb import BBImporter
from importers.nu import NUImporter
from importers.cibic_checking import CIBICCheckingImporter
from importers.cibic_savings import CIBICSavingsImporter
from importers.c6_checking import C6CheckingImporter
from rabbitmq.producer import publish_import_batch
from utils.logger import get_logger

logger = get_logger("routers.import_router")

router = APIRouter(prefix="/api/v1/import", tags=["import"])

_security = HTTPBearer(auto_error=False)

IMPORTERS = {
    "pcfinancial": PCFinancialImporter,
    "mbna": MBNACardImporter,
    "rbc": RBCImporter,
    "bb": BBImporter,
    "nu": NUImporter,
    "cibic-checking": CIBICCheckingImporter,
    "cibic-savings": CIBICSavingsImporter,
    "c6-checking": C6CheckingImporter,
}

ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/octet-stream", "text/plain"}


def _verify_token(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Forward token validation to the account-service / Keycloak.

    The import-service trusts that Traefik (or a gateway) has already validated
    the Bearer token before routing the request here.  For defence-in-depth we
    still require an Authorization header to be present.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    return credentials.credentials


@router.post("/{importer_type}")
async def import_csv(
    importer_type: str,
    file: UploadFile = File(...),
    _token: str = Depends(_verify_token),
):
    """Upload a CSV file and dispatch its transactions to the RabbitMQ import queue.

    Parameters
    ----------
    importer_type:
        One of: pcfinancial, mbna, rbc, bb, nu, cibic-checking,
        cibic-savings, c6-checking
    file:
        The CSV file exported from the bank.
    """
    if importer_type not in IMPORTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown importer '{importer_type}'. "
                   f"Allowed values: {sorted(IMPORTERS.keys())}",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {file.content_type}",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Write to a named temp file so pandas can read it via file path
    suffix = os.path.splitext(file.filename or "upload.csv")[1] or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        importer = IMPORTERS[importer_type]()
        transactions = importer.parse(tmp_path)
    except Exception as exc:
        logger.exception("Failed to parse CSV for importer '%s': %s", importer_type, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse CSV: {exc}",
        ) from exc
    finally:
        os.unlink(tmp_path)

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No transactions found in the uploaded file",
        )

    # Enrich with fingerprint before publishing
    for t in transactions:
        t["fingerprint"] = generate(t)

    try:
        import_id = await publish_import_batch(importer_type, transactions)
    except Exception as exc:
        logger.exception("Failed to publish to RabbitMQ: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to publish transactions to the import queue. Please try again.",
        ) from exc

    return {
        "import_id": import_id,
        "importer": importer_type,
        "queued_count": len(transactions),
        "message": "Transactions queued for import successfully",
    }
