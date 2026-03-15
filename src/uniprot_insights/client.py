from __future__ import annotations

import random
import time
from typing import Dict, List, Optional

import httpx

from .cache import CacheBackend, InMemoryCache
from .exceptions import UniProtAPIError, UniProtNotFoundError


class UniProtClient:
    def __init__(
        self,
        *,
        base_url: str = "https://rest.uniprot.org/uniprotkb",
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.25,
        cache: Optional[CacheBackend] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.cache = cache or InMemoryCache()
        self._client = http_client or httpx.Client(timeout=timeout)

    def _wait_before_retry(self, attempt: int) -> None:
        jitter = random.uniform(0.0, 0.2)
        sleep_for = (2 ** attempt) * self.backoff_seconds + jitter
        time.sleep(sleep_for)

    def fetch_entry(self, accession: str) -> Dict:
        accession = accession.strip()
        if not accession:
            raise UniProtAPIError("Accession must be a non-empty string")

        if self.cache:
            cached = self.cache.get(accession)
            if cached is not None:
                return cached

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(
                    f"{self.base_url}/{accession}",
                    headers={"Accept": "application/json"},
                    timeout=self.timeout,
                )
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    self._wait_before_retry(attempt)
                    continue
                raise UniProtAPIError(f"Request failed for {accession}: {exc}") from exc

            if response.status_code == 404:
                raise UniProtNotFoundError(f"UniProt accession not found: {accession}")

            if response.status_code in {429} or 500 <= response.status_code < 600:
                last_exc = UniProtAPIError(f"Transient UniProt error ({response.status_code}) for {accession}")
                if attempt < self.max_retries - 1:
                    self._wait_before_retry(attempt)
                    continue
                raise last_exc

            if response.status_code >= 400:
                raise UniProtAPIError(
                    f"Failed fetching {accession}: HTTP {response.status_code} {response.text}"
                )

            payload = response.json()
            if self.cache:
                self.cache.set(accession, payload)
            return payload

        if last_exc is not None:
            raise last_exc
        raise UniProtAPIError(f"Unknown failure while fetching {accession}")

    def fetch_many(self, accessions: List[str]) -> List[Dict]:
        entries: List[Dict] = []
        for accession in accessions:
            entries.append(self.fetch_entry(accession))
        return entries
