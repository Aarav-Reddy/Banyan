#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
make demo
printf '\nBanyan is available at http://127.0.0.1:8080\n'
read -r -p 'Press Return to close this window. The demo services keep running.'
