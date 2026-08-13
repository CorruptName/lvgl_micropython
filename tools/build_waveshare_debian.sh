#!/usr/bin/env bash
# Local development builder for only the Waveshare ESP-NOW variant. This may
# reuse incremental caches and is not a substitute for a firmware-v* release.
set -euo pipefail

IMAGE="lvgl-micropython-idf:v5.5.1"
HOSTED_REPOSITORY="https://github.com/CorruptName/esp-hosted-mcu.git"
HOSTED_COMMIT="dd95bdf3316fc8c6110b387855033a26c0aa2447"
TOML="display_configs/Waveshare-ESP32-P4-WIFI6-Touch-LCD-4.3.toml"
BUILD_ROOT="${LVGL_MICROPYTHON_BUILD_ROOT:-$HOME/esp-idf/lvgl_micropython-build}"
SOURCE=""
MODE="espnow"
CLEAN=0

while (($#)); do
    case "$1" in
        --source)
            SOURCE="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --clean)
            CLEAN=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "$SOURCE" || ! -f "$SOURCE/make.py" ]]; then
    echo "A valid --source path is required." >&2
    exit 2
fi
if [[ "$MODE" != "espnow" ]]; then
    echo "Unsupported mode: $MODE" >&2
    exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is unavailable. Enable Docker Desktop integration for this WSL distribution." >&2
    exit 1
fi
if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync is required." >&2
    exit 1
fi

mkdir -p "$BUILD_ROOT"
if ((CLEAN)); then
    rm -rf "$BUILD_ROOT/build" \
        "$BUILD_ROOT/lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI"
fi

echo "Syncing source to native Linux workspace: $BUILD_ROOT"
rsync -a --delete --no-owner --no-group \
    --exclude '/.venv/' \
    --exclude '/build/' \
    --exclude '/build_artifacts/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '/lib/micropython/ports/esp32/build-*/' \
    --exclude '/lib/micropython/ports/esp32/managed_components/' \
    --exclude '/lib/micropython/ports/esp32/components/' \
    "$SOURCE/" "$BUILD_ROOT/"

HOSTED_PATH="$BUILD_ROOT/lib/micropython/ports/esp32/components/espressif__esp_hosted"
if [[ ! -d "$HOSTED_PATH/.git" ]]; then
    rm -rf "$HOSTED_PATH"
    mkdir -p "$(dirname "$HOSTED_PATH")"
    git clone --quiet --recurse-submodules "$HOSTED_REPOSITORY" "$HOSTED_PATH"
fi
if [[ "$(git -C "$HOSTED_PATH" rev-parse HEAD)" != "$HOSTED_COMMIT" ]]; then
    git -C "$HOSTED_PATH" fetch --quiet origin "$HOSTED_COMMIT"
    git -C "$HOSTED_PATH" checkout --quiet "$HOSTED_COMMIT"
fi
git -C "$HOSTED_PATH" submodule update --init --recursive --quiet

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Building pinned toolchain image: $IMAGE"
    docker build -q -t "$IMAGE" -f "$BUILD_ROOT/tools/docker/esp32-p4.Dockerfile" "$BUILD_ROOT/tools/docker"
fi

uid="$(id -u)"
gid="$(id -g)"
echo "Building Waveshare ESP-NOW firmware with ESP-IDF v5.5.1..."
built="$BUILD_ROOT/build/lvgl_micropy_ESP32_GENERIC_P4-C6_WIFI-32.bin"
rm -f "$built"
build_args=(python3 make.py --toml="$TOML")
if ((!CLEAN)); then
    rm -f \
        "$BUILD_ROOT/lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI/lv_mp.c" \
        "$BUILD_ROOT/lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI/lv_mp.c.json" \
        "$BUILD_ROOT/lib/micropython/ports/esp32/build-ESP32_GENERIC_P4-C6_WIFI/lvgl_api.json"
    build_args+=(--incremental)
fi
docker run --rm \
    --mount "type=bind,source=$BUILD_ROOT,target=/workspace" \
    --workdir /workspace \
    "$IMAGE" \
    bash -lc "set -e; trap 'chown -R $uid:$gid /workspace' EXIT; git config --global --add safe.directory '*'; ${build_args[*]}"

if [[ ! -f "$built" ]]; then
    echo "Expected firmware was not produced: $built" >&2
    exit 1
fi

artifact_dir="$SOURCE/build_artifacts"
artifact="$artifact_dir/waveshare-esp32-p4-4.3-espnow.bin"
mkdir -p "$artifact_dir"
cp "$built" "$artifact"
(cd "$artifact_dir" && sha256sum "$(basename "$artifact")") | tee "$artifact.sha256"
echo "Firmware copied to: $artifact"
