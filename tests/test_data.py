from mobius.commons.data import chunk, file_md5, reverse_map


def test_chunk_splits_evenly():
    assert list(chunk([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]


def test_chunk_last_chunk_smaller():
    assert list(chunk([1, 2, 3], 2)) == [[1, 2], [3]]


def test_chunk_empty():
    assert list(chunk([], 10)) == []


def test_reverse_map():
    assert reverse_map({"a": 1, "b": 2}) == {1: "a", 2: "b"}


def test_file_md5(tmp_path):
    file = tmp_path / "data.bin"
    file.write_bytes(b"hello")

    assert file_md5(file) == "5d41402abc4b2a76b9719d911017c592"


def test_file_md5_large_file_spans_chunks(tmp_path):
    file = tmp_path / "data.bin"
    file.write_bytes(b"x" * 20000)

    import hashlib

    assert file_md5(file) == hashlib.md5(b"x" * 20000).hexdigest()
