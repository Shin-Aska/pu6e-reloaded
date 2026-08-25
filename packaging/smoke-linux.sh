#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" != 1 ]]; then
    printf 'Usage: %s /absolute/or/relative/path/to/executable\n' "$0" >&2
    exit 2
fi

application_path="$(realpath -- "$1")"
runtime_directory="$(mktemp -d -t pu6e-smoke.XXXXXX)"
export XDG_CONFIG_HOME="$runtime_directory/config"

"$application_path" >"$runtime_directory/launcher.log" 2>&1 &
application_pid=$!
trap 'kill "$application_pid" 2>/dev/null || true' EXIT

for attempt in {1..150}; do
    if ! kill -0 "$application_pid" 2>/dev/null; then
        sed -n '1,160p' "$runtime_directory/launcher.log" >&2
        printf 'The packaged launcher exited before creating its window.\n' >&2
        exit 1
    fi

    if xwininfo -root -tree | grep -F 'pu6e Reloaded' >/dev/null; then
        printf 'Verified packaged launcher window: %s\n' "$application_path"
        exit 0
    fi

    sleep 0.2
done

sed -n '1,160p' "$runtime_directory/launcher.log" >&2
printf 'Timed out waiting for the packaged launcher window.\n' >&2
exit 1
