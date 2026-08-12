from typing import Final


MAX_CHUNK_SIZE: Final[int]


def begin() -> None:
    """Prepare the C6 inactive OTA application partition."""


def write(data: bytes | bytearray | memoryview) -> int:
    """Send one application-image chunk of at most MAX_CHUNK_SIZE bytes."""


def end() -> None:
    """Finalize and validate the transferred C6 application image."""


def activate() -> None:
    """Boot the successfully finalized C6 OTA image."""