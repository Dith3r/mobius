import logging
import os

import backoff
import httpx


logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)


@backoff.on_exception(
    backoff.expo, (httpx.HTTPStatusError, httpx.ConnectError), max_time=60
)
def _resolve_verify(value: str):
    if value.lower() in ("false", "0", "no"):
        return False
    if value.lower() in ("true", "1", "yes"):
        return True
    return value  # treat as path to a CA bundle


def wait_for_opensearch():
    host = os.environ.get("OPENSEARCH_SERVER")
    auth = (
        os.environ.get("OPENSEARCH_USERNAME"),
        os.environ.get("OPENSEARCH_PASSWORD"),
    )
    verify = _resolve_verify(os.environ.get("OPENSEARCH_SSL_VERIFY", "true"))

    with httpx.Client(base_url=host, auth=auth, verify=verify) as client:
        headers = {"Content-Type": "application/json"}
        response = client.get(
            "_cluster/health",
            headers=headers,
        )
        response.raise_for_status()
    logging.info("Connection succeeded!")


def main():
    wait_for_opensearch()


if __name__ == "__main__":
    main()
