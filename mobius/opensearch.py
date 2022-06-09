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
def wait_for_opensearch():
    host = os.environ.get("OPENSEARCH_SERVER")
    auth = (
        os.environ.get("OPENSEARCH_USERNAME"),
        os.environ.get("OPENSEARCH_PASSWORD"),
    )

    with httpx.Client(base_url=host, auth=auth, verify=False) as client:
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
