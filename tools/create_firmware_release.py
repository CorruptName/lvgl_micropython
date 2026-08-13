#!/usr/bin/env python3
"""Create an immutable installer-firmware release index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


REPOSITORY = Path(__file__).resolve().parents[1]
VARIANTS = {
    "dev-standard": {
        "filename": "esp32-p4.bin",
        "package_path": "firmware/p4/esp32-p4.bin",
        "device": "dev",
        "espnow": False,
    },
    "dev-espnow": {
        "filename": "esp32-p4-espnow.bin",
        "package_path": "firmware/p4/esp32-p4-espnow.bin",
        "device": "dev",
        "espnow": True,
    },
    "waveshare-standard": {
        "filename": "waveshare-esp32-p4-4.3.bin",
        "package_path": "firmware/p4/waveshare-esp32-p4-4.3.bin",
        "device": "waveshare",
        "espnow": False,
    },
    "waveshare-espnow": {
        "filename": "waveshare-esp32-p4-4.3-espnow.bin",
        "package_path": "firmware/p4/waveshare-esp32-p4-4.3-espnow.bin",
        "device": "waveshare",
        "espnow": True,
    },
}


def git(*args: str, directory: Path = REPOSITORY) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()

    artifacts = {}
    for artifact_id, definition in VARIANTS.items():
        path = output / definition["filename"]
        if not path.is_file():
            raise FileNotFoundError(path)
        artifacts[artifact_id] = {
            **definition,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }

    metadata = {
        "schema_version": 1,
        "producer": {
            "repository": "https://github.com/CorruptName/lvgl_micropython",
            "commit": git("rev-parse", "HEAD"),
            "git_ref": git("describe", "--tags", "--always", "HEAD"),
            "micropython_commit": git(
                "rev-parse", "HEAD", directory=REPOSITORY / "lib/micropython"
            ),
            "lvgl_commit": git(
                "rev-parse", "HEAD", directory=REPOSITORY / "lib/lvgl"
            ),
            "esp_idf_commit": git(
                "rev-parse", "HEAD", directory=REPOSITORY / "lib/esp-idf"
            ),
            "esp_hosted_commit": "dd95bdf3316fc8c6110b387855033a26c0aa2447",
        },
        "radio_compatibility": {
            "esp_hosted_protocol": "2.7.0",
            "c6_elf_sha256": (
                "85544ac1fa10fee3b652525141b2c51d3aecac89e56e8d88a4dded594b56eef4"
            ),
        },
        "artifacts": artifacts,
    }

    index = output / "firmware-release.json"
    index.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    checksum_lines = [
        f"{artifacts[artifact_id]['sha256']}  {definition['filename']}"
        for artifact_id, definition in VARIANTS.items()
    ]
    checksum_lines.append(f"{sha256(index)}  {index.name}")
    (output / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="ascii",
    )
    print(f"Created {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
