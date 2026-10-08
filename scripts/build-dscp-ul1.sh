#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
tag=v2.8.0-r1-dscp-ul1
out=artifacts/dscp-ul1
mkdir -p "$out"
exec > >(tee "$out/build.log") 2>&1
# This offline build reuses immutable original compiler/runtime images.
# Reconstruct the original base with the standard Dockerfile if absent.
python3 - <<'PY'
import json,subprocess
for tag,expected in json.load(open('release-dscp-ul1.lock.json')).items():
 actual=json.loads(subprocess.check_output(['docker','image','inspect',tag]))[0]['Id']
 assert actual==expected, (tag,actual,expected)
PY
patch=$(sha256sum images/base-open5gs/patches/dscp-ul1.patch | cut -d' ' -f1)
source=$(git rev-parse HEAD)
docker build --network none --pull=false -f images/base-open5gs/Dockerfile.dscp-ul1 \
 -t "base-open5gs:$tag" images/base-open5gs
for nf in pcf smf upf; do
 docker build --network none --pull=false \
  --build-arg "RUNTIME_BASE=ghcr.io/llleixx/open5gs-$nf:v2.8.0-r1" --build-arg "NF=$nf" \
  --label "org.opencontainers.image.version=$tag" \
  --label "org.opencontainers.image.revision=157f611a530e292e40ec50f9d23f0ef5d4fcd6a6" \
  --label "org.opencontainers.image.source=https://github.com/llleixx/docker-open5gs" \
  --label "huizhou.build-revision=$source" --label "huizhou.patch-sha256=$patch" \
  -t "ghcr.io/llleixx/open5gs-$nf:$tag" images/dscp-ul1
done
docker image inspect "ghcr.io/llleixx/open5gs-pcf:$tag" "ghcr.io/llleixx/open5gs-smf:$tag" "ghcr.io/llleixx/open5gs-upf:$tag" > "$out/images.json"
docker save "ghcr.io/llleixx/open5gs-pcf:$tag" "ghcr.io/llleixx/open5gs-smf:$tag" "ghcr.io/llleixx/open5gs-upf:$tag" | gzip > "$out/open5gs-$tag.tar.gz"
sha256sum "$out/open5gs-$tag.tar.gz" > "$out/SHA256SUMS"
