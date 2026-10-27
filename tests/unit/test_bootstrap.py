import os

import pytest

from sakila_experiment.bootstrap import BootstrapError, private_file


def test_secret_file_is_private_and_never_rotates_silently(tmp_path):
    path = tmp_path / "secrets" / "reader_password.txt"
    private_file(path, "first-secret")
    assert path.stat().st_mode & 0o077 == 0
    private_file(path, "second-secret")
    assert path.read_text() == "first-secret"
    os.chmod(path, 0o644)
    with pytest.raises(BootstrapError):
        private_file(path, "third-secret")

