#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
exec > >(tee -a artifacts/build.log) 2>&1
# Lock base images before building. Existing lock files are never refreshed implicitly.
python3 scripts/lock-release.py
mapfile -t bases < <(python3 -c 'import json; d=json.load(open("release.lock.json")); print(d["bases"]["ubuntu"]); print(d["bases"]["node_build"]); print(d["bases"]["node_runtime"])')
args=(--network host --platform linux/amd64 --build-arg OPEN5GS_VERSION=v2.8.0 --build-arg OPEN5GS_COMMIT=157f611a530e292e40ec50f9d23f0ef5d4fcd6a6 --build-arg "UBUNTU_VERSION=${bases[0]#ubuntu:}" --build-arg BUILD_JOBS=4 --build-arg UBUNTU_MIRROR=http://mirrors.ustc.edu.cn/ubuntu)
for key in HTTP_PROXY HTTPS_PROXY NO_PROXY; do
  [[ -z "${!key:-}" ]] || args+=(--build-arg "$key")
done
docker build "${args[@]}" -t base-open5gs:v2.8.0 images/base-open5gs
for nf in nrf ausf udm udr nssf bsf pcf amf smf upf; do
  docker build "${args[@]}" --label org.opencontainers.image.source=https://github.com/llleixx/docker-open5gs --label org.opencontainers.image.version=v2.8.0-r1 --label org.opencontainers.image.revision=157f611a530e292e40ec50f9d23f0ef5d4fcd6a6 -t "ghcr.io/llleixx/open5gs-$nf:v2.8.0-r1" "images/$nf"
done
docker build "${args[@]}" --build-arg "NODE_BUILD_IMAGE=${bases[1]}" --build-arg "NODE_RUNTIME_IMAGE=${bases[2]}" --label org.opencontainers.image.source=https://github.com/llleixx/docker-open5gs --label org.opencontainers.image.version=v2.8.0-r1 --label org.opencontainers.image.revision=157f611a530e292e40ec50f9d23f0ef5d4fcd6a6 -t ghcr.io/llleixx/open5gs-webui:v2.8.0-r1 images/webui
python3 scripts/verify-images.py
