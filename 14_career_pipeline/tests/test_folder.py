import pytest

from careerpipe.folder import ApplicationFolder


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "abgelehnt" / "Acme Logistik").mkdir(parents=True)
    (tmp_path / "Beispiel GmbH").mkdir()
    (tmp_path / "Lebenslauf.pdf").write_bytes(b"%PDF")
    return ApplicationFolder(tmp_path)


def test_reading_works(folder):
    with folder.open("Lebenslauf.pdf") as f:
        assert f.read() == b"%PDF"


@pytest.mark.parametrize("mode", ["w", "wb", "a", "r+", "x"])
def test_every_write_mode_is_refused(folder, mode):
    with pytest.raises(PermissionError):
        folder.open("Lebenslauf.pdf", mode)


def test_the_file_is_unchanged_after_a_refused_write(folder):
    with pytest.raises(PermissionError):
        folder.open("Lebenslauf.pdf", "w")
    assert (folder.root / "Lebenslauf.pdf").read_bytes() == b"%PDF"


def test_paths_outside_the_folder_are_refused(folder):
    with pytest.raises(PermissionError):
        folder.open("../elsewhere.txt")


def test_subfolders_list_the_applications(folder):
    assert folder.subfolders() == ["Beispiel GmbH", "abgelehnt"]
    assert folder.subfolders("abgelehnt") == ["Acme Logistik"]


def test_a_missing_folder_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        ApplicationFolder(tmp_path / "nope")


def test_the_pipeline_folder_is_skipped_when_reading(tmp_path):
    (tmp_path / "Pipeline" / "out").mkdir(parents=True)
    (tmp_path / "Pipeline" / "config.yaml").write_text("contact: secret", encoding="utf-8")
    (tmp_path / "Lebenslauf.pdf").write_bytes(b"%PDF")
    folder = ApplicationFolder(tmp_path, skip="Pipeline")
    assert [str(p) for p in folder.files()] == ["Lebenslauf.pdf"]
    assert folder.subfolders() == []
