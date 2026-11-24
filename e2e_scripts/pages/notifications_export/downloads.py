"""Where Playwright saved a download."""

from pathlib import Path

from playwright.sync_api import Download


class MissingDownloadError(FileNotFoundError):
    def __init__(self, file_name: str) -> None:
        super().__init__(f"Download {file_name} has no local file")


def saved_file(download: Download) -> Path:
    path = download.path()
    if path is None:
        raise MissingDownloadError(download.suggested_filename)
    return path
