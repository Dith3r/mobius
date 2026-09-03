import shutil
import subprocess

import pytest


def docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False

    try:
        return (
            subprocess.run(
                [docker, "info"], capture_output=True, timeout=20
            ).returncode
            == 0
        )
    except subprocess.SubprocessError:
        return False


def pytest_collection_modifyitems(config, items):
    if docker_available():
        return

    skip = pytest.mark.skip(reason="docker is not available")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def postgres_url():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver=None) as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def mongo_url():
    from testcontainers.mongodb import MongoDbContainer

    with MongoDbContainer("mongo:7") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(27017)
        yield f"mongodb://test:test@{host}:{port}/mobius?authSource=admin"


@pytest.fixture(scope="session")
def mysql_config():
    from testcontainers.mysql import MySqlContainer

    with MySqlContainer("mysql:8.4") as container:
        yield {
            "host": container.get_container_host_ip(),
            "port": int(container.get_exposed_port(3306)),
            "database": container.dbname,
            "user": container.username,
            "password": container.password,
            "connect_timeout": 10,
        }


@pytest.fixture(scope="session")
def consul_address():
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    container = (
        DockerContainer("hashicorp/consul:1.21")
        .with_exposed_ports(8500)
        .with_command("agent -dev -client=0.0.0.0")
    )

    with container:
        wait_for_logs(container, "Consul agent running!", timeout=60)

        host = container.get_container_host_ip()
        port = container.get_exposed_port(8500)
        yield f"http://{host}:{port}"


@pytest.fixture(scope="session")
def redpanda_bootstrap():
    from testcontainers.kafka import RedpandaContainer

    with RedpandaContainer() as container:
        yield container.get_bootstrap_server()
