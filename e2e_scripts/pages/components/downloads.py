"""Collecting the files a page downloads without waiting for one."""

from playwright.sync_api import Download, Page


def collect_downloads(page: Page) -> list[Download]:
    """The returned list fills with every download that follows.

    Why a nested function: Playwright's sync `page.on` tags the handler it is given, and a bound built-in
    such as `list.append` cannot be tagged (AttributeError `_pw_impl_instance_`)."""
    downloads: list[Download] = []

    def keep(download: Download) -> None:
        downloads.append(download)

    page.on("download", keep)
    return downloads
