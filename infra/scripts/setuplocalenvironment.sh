#!/bin/bash
set -euo pipefail
./infra/scripts/createlocalsettings.sh
./infra/scripts/addclientip.sh
