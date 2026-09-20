"""Opt-in bounded official-source fetches with pinned DNS and no redirects."""

import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit

from .common import MAX_BYTES, MAX_SECONDS, ImportProblem

SOURCES = {
    "irs_index_2023": "https://apps.irs.gov/pub/epostcard/990/xml/2023/index_2023.csv",
    "irs_schema_2022": "https://www.irs.gov/pub/irs-tege/990x-schema-2022v5-0.zip",
    "irs_schema_2023": "https://www.irs.gov/pub/irs-tege/990x-schema-2023v5-1.zip",
    "irs_schema_2024": "https://www.irs.gov/pub/irs-tege/990x-schema-2024v5.0.zip",
    "acs_baltimore_2023": "https://api.census.gov/data/2023/acs/acs5?get=NAME,B17001_001E,B17001_001M,B17001_002E,B17001_002M,B17001_001EA,B17001_001MA,B17001_002EA,B17001_002MA&for=county:510&in=state:24",
}


def validate_url(url):
    if url not in SOURCES.values():
        raise ImportProblem("source_not_allowed", "URL is not an approved official source request.")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.port not in (None, 443)
    ):
        raise ImportProblem("unsafe_source_url", "Official sources require credential-free HTTPS.")
    return parsed


def public_addresses(host):
    addresses = sorted(
        {entry[4][0] for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    )
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ImportProblem(
            "private_destination", "Source resolves to a nonpublic network destination."
        )
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        self.tls_context = ssl.create_default_context()
        super().__init__(host, timeout=timeout, context=self.tls_context)
        self.address = address

    def connect(self):
        # Connect to the validated numeric address; TLS still verifies the original hostname.
        sock = socket.create_connection((self.address, self.port), self.timeout)
        self.sock = self.tls_context.wrap_socket(sock, server_hostname=self.host)


def fetch_source(source_id: str, *, enabled: bool = False) -> bytes:
    if not enabled:
        raise ImportProblem(
            "network_disabled", "Public-source network access requires explicit opt-in."
        )
    if source_id not in SOURCES:
        raise ImportProblem("source_not_allowed", "Unknown official source identifier.")
    parsed = validate_url(SOURCES[source_id])
    started = time.monotonic()
    addresses = public_addresses(parsed.hostname)
    connection = PinnedHTTPSConnection(parsed.hostname, addresses[0], timeout=5)
    try:
        connection.request(
            "GET",
            parsed.path + ("?" + parsed.query if parsed.query else ""),
            headers={"Accept-Encoding": "identity", "User-Agent": "Banyan-pilot/0.1"},
        )
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise ImportProblem(
                "redirect_rejected",
                "Source redirected; credentials or a reviewed catalog update may be required.",
            )
        if response.status != 200:
            raise ImportProblem(
                "source_unavailable", "Official source returned an unsuccessful response."
            )
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ImportProblem("content_encoding", "Compressed HTTP responses are not accepted.")
        length = response.getheader("Content-Length")
        if length and (not length.isdigit() or int(length) > MAX_BYTES):
            raise ImportProblem(
                "source_too_large", "Use a bounded local source excerpt; response exceeds 5 MiB."
            )
        chunks = []
        size = 0
        while True:
            if time.monotonic() - started > MAX_SECONDS:
                raise ImportProblem("time_limit", "Source fetch exceeded its total time limit.")
            chunk = response.read(min(65536, MAX_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ImportProblem("source_too_large", "Source exceeded the response limit.")
            chunks.append(chunk)
        return b"".join(chunks)
    except (OSError, http.client.HTTPException) as exc:
        raise ImportProblem(
            "source_unavailable", "Official source could not be retrieved securely."
        ) from exc
    finally:
        connection.close()
