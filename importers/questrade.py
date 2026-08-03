from datetime import UTC, datetime
from typing import Any

import httpx


class QuestradeImporter:
    ACCOUNT_CODE = "QUESTTFSA"
    LOGIN_URL = "https://login.questrade.com/oauth2/token"
    PRACTICE_LOGIN_URL = "https://practicelogin.questrade.com/oauth2/token"

    async def fetch_transactions(
        self,
        refresh_token: str,
        start_date: str,
        end_date: str,
        account_number: str | None = None,
        is_practice: bool = False,
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_payload = await self._redeem_refresh_token(
                client=client,
                refresh_token=refresh_token,
                is_practice=is_practice,
            )

            account = await self._resolve_account(
                client=client,
                api_server=token_payload["api_server"],
                access_token=token_payload["access_token"],
                account_number=account_number,
            )

            activities = await self._fetch_activities(
                client=client,
                api_server=token_payload["api_server"],
                access_token=token_payload["access_token"],
                account_number=account["number"],
                start_date=start_date,
                end_date=end_date,
            )

        transactions = []
        for activity in activities:
            mapped = self._map_activity(activity)
            if mapped:
                transactions.append(mapped)

        return transactions

    async def _redeem_refresh_token(
        self,
        client: httpx.AsyncClient,
        refresh_token: str,
        is_practice: bool,
    ) -> dict[str, Any]:
        login_url = self.PRACTICE_LOGIN_URL if is_practice else self.LOGIN_URL
        response = await client.get(
            login_url,
            params={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        response.raise_for_status()
        payload = response.json()

        if not payload.get("access_token") or not payload.get("api_server"):
            raise ValueError("Questrade token response is missing access details")

        return payload

    async def _resolve_account(
        self,
        client: httpx.AsyncClient,
        api_server: str,
        access_token: str,
        account_number: str | None,
    ) -> dict[str, Any]:
        response = await client.get(
            f"{api_server.rstrip('/')}/v1/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()

        accounts = response.json().get("accounts", [])
        if not accounts:
            raise ValueError("No Questrade accounts were returned")

        if account_number:
            for account in accounts:
                if str(account.get("number")) == str(account_number):
                    return account
            raise ValueError(f"Questrade account '{account_number}' was not found")

        tfsa_accounts = [
            account
            for account in accounts
            if str(account.get("type", "")).upper() == "TFSA"
        ]
        if len(tfsa_accounts) == 1:
            return tfsa_accounts[0]
        if len(accounts) == 1:
            return accounts[0]

        raise ValueError(
            "Multiple Questrade accounts found. Provide accountNumber in the request."
        )

    async def _fetch_activities(
        self,
        client: httpx.AsyncClient,
        api_server: str,
        access_token: str,
        account_number: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        response = await client.get(
            f"{api_server.rstrip('/')}/v1/accounts/{account_number}/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "startTime": f"{start_date}T00:00:00Z",
                "endTime": f"{end_date}T23:59:59Z",
            },
        )
        response.raise_for_status()
        return response.json().get("activities", [])

    def _map_activity(self, activity: dict[str, Any]) -> dict[str, Any] | None:
        activity_kind = self._classify_activity(activity)
        if activity_kind is None:
            return None

        amount = self._extract_amount(activity)
        if amount == 0:
            return None

        normalized_amount = abs(amount) if activity_kind == "deposit" else -abs(amount)
        description = self._build_description(activity, activity_kind)

        return {
            "account_code": self.ACCOUNT_CODE,
            "datetime": self._normalize_datetime(activity),
            "amount": normalized_amount,
            "description": description,
            "transaction_type_code": "PAYMENT",
        }

    def _classify_activity(self, activity: dict[str, Any]) -> str | None:
        searchable_fields = [
            activity.get("type"),
            activity.get("action"),
            activity.get("description"),
            activity.get("symbol"),
            activity.get("currency"),
            activity.get("settlementDate"),
        ]
        haystack = " ".join(str(value or "") for value in searchable_fields).upper()

        if "DEPOSIT" in haystack or "CONTRIBUTION" in haystack:
            return "deposit"
        if "WITHDRAW" in haystack or "WITHDRAWAL" in haystack:
            return "withdrawal"

        return None

    def _extract_amount(self, activity: dict[str, Any]) -> float:
        for field in ("netAmount", "amount", "grossAmount"):
            value = activity.get(field)
            if value is not None:
                return float(value)
        return 0.0

    def _build_description(self, activity: dict[str, Any], activity_kind: str) -> str:
        description = str(activity.get("description") or "").strip()
        action = str(activity.get("action") or "").strip()

        if description:
            return description
        if action:
            return action

        return "Questrade deposit" if activity_kind == "deposit" else "Questrade withdrawal"

    def _normalize_datetime(self, activity: dict[str, Any]) -> str:
        raw_value = (
            activity.get("transactionDate")
            or activity.get("settlementDate")
            or activity.get("tradeDate")
            or activity.get("timestamp")
        )

        if not raw_value:
            raise ValueError("Questrade activity is missing a transaction date")

        text = str(raw_value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d 00:00:00")

        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)

        return dt.strftime("%Y-%m-%d %H:%M:%S")