#!/usr/bin/env bash
#
# Regenerate the browser app's TypeScript types from the server's own
# description of itself.
#
# The server (FastAPI) publishes a machine-readable description of every route
# it serves and every data shape those routes return. This script asks the
# server program for that description without starting a web server, hands it to
# `openapi-typescript`, and writes the result to frontend/src/api/schema.ts.
#
# That file is committed. A build job runs this script again and fails if the
# result differs, which is what stops the two halves of the app from drifting
# apart: change a data shape on the server without regenerating, and the build
# goes red instead of the browser breaking later.
#
# Nothing in this file is hand-written afterwards. If a generated type is
# unpleasant to use, fix the data shape on the server and run this again.
#
# Run it from anywhere:
#
#     ./scripts/gen-types.sh

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
backend_dir="${repo_root}/backend"
frontend_dir="${repo_root}/frontend"
output_file="${frontend_dir}/src/api/schema.ts"

if ! command -v uv >/dev/null 2>&1; then
  echo "gen-types: uv is not installed, and it is what runs the server's Python. Install it from https://docs.astral.sh/uv/getting-started/installation/ and run this again." >&2
  exit 1
fi

if [ ! -d "${frontend_dir}/node_modules" ]; then
  echo "gen-types: the browser app's packages are not installed, and openapi-typescript is one of them. Run 'npm ci' inside ${frontend_dir} and run this again." >&2
  exit 1
fi

mkdir -p "$(dirname -- "${output_file}")"

# `uv run` prints its own progress to standard error; only the description
# itself comes out on standard output, so the pipe below carries just the
# description.
(
  cd -- "${backend_dir}"
  uv run python -c "from katalyst.api.main import app; import json; print(json.dumps(app.openapi()))"
) | npm --prefix "${frontend_dir}" exec --no -- openapi-typescript --output "${output_file}"

echo "gen-types: wrote ${output_file}"
