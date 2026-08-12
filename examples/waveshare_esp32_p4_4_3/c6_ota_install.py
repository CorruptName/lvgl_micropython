import binascii
import hashlib

import c6_ota


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as image:
        while True:
            chunk = image.read(4096)
            if not chunk:
                break
            digest.update(chunk)
    return binascii.hexlify(digest.digest()).decode()


def install(path, expected_sha256, activate=False):
    expected_sha256 = expected_sha256.lower()
    actual_sha256 = file_sha256(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            "C6 image SHA-256 mismatch: expected {}, got {}".format(
                expected_sha256, actual_sha256
            )
        )

    with open(path, "rb") as image:
        if image.read(1) != b"\xe9":
            raise ValueError("file is not an ESP application image")
        image.seek(0)

        c6_ota.begin()
        total = 0
        while True:
            chunk = image.read(c6_ota.MAX_CHUNK_SIZE)
            if not chunk:
                break
            total += c6_ota.write(chunk)
            print("Transferred {} bytes".format(total))

    c6_ota.end()
    print("C6 application image validated ({} bytes)".format(total))

    if activate:
        print("Activating C6 application image")
        c6_ota.activate()
    else:
        print("Run c6_ota.activate() to boot the new C6 image")


if __name__ == "__main__":
    raise RuntimeError("import install() and provide the expected SHA-256 explicitly")