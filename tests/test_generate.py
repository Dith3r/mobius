import pytest

from mobius.commands.generate import (
    DestinationNotDirectoryException,
    GenerateCommand,
)


def test_generate_creates_migration_file(tmp_path):
    GenerateCommand().execute(str(tmp_path))

    files = list(tmp_path.glob("*.py"))
    assert len(files) == 1

    migration_id = files[0].stem
    contents = files[0].read_text()

    assert f"class Migration{migration_id}(Migration)" in contents
    assert "def execute(self)" in contents
    assert "def validate(self)" in contents


def test_generated_file_is_valid_python(tmp_path):
    GenerateCommand().execute(str(tmp_path))

    file = next(tmp_path.glob("*.py"))
    compile(file.read_text(), str(file), "exec")


def test_generate_rejects_missing_directory(tmp_path):
    with pytest.raises(DestinationNotDirectoryException):
        GenerateCommand().execute(str(tmp_path / "nope"))
