# Open5GS v2.8.0 release

## Sources and images

- Upstream container project: Borjis131/docker-open5gs, base commit `10295cfecb2f86f88944df1728127853eb4d6a1f`.
- Open5GS tag `v2.8.0`, verified source commit `157f611a530e292e40ec50f9d23f0ef5d4fcd6a6`.
- `release.lock.json` records the source and base image digests. APT packages are mirror-resolved, so exact delivered image IDs and archives are the reproducibility boundary; rebuilds can change when distro repositories change.
- Components: nrf, ausf, udm, udr, nssf, bsf, pcf, amf, smf, upf, webui.
- Image format: `ghcr.io/llleixx/open5gs-<component>:v2.8.0-r1`, linux/amd64. Images are loaded offline, not automatically published.

## Build

Requires Linux, Docker Engine/BuildKit, Python 3 and network access. Build from the repository root:

```sh
bash scripts/build-release.sh
python3 scripts/verify-images.py
```

The first build needs Ubuntu jammy, node:20-bookworm and node:20-bookworm-slim locally available to create a missing lock file. Existing lock files are reused. HTTP_PROXY/HTTPS_PROXY/NO_PROXY may be supplied locally, never committed. The build uses host networking, a four-job native compiler, and a selectable Ubuntu APT mirror. Native Dockerfiles retain upstream component-specific runtime libraries and entrypoints.

`python3 scripts/export-release.py` exports all eleven images and writes SHA256SUMS.

`artifacts/images.json` contains verified runtime versions and image IDs. `artifacts/` and `private/` are ignored. Never put subscriber exports, production environment files, WebUI secrets, or backups in tracked files.

## Isolated acceptance

`tests/lab/compose.json` uses independent bridge networks 10.250.80/81/82.0/24 and UE pools 10.250.83/84/85.0/24. It must not connect to a production RAN. The three synthetic IMSIs and test authentication keys in `seed.js` and `ue*.yaml` are lab fixtures only.

Run `bash tests/lab/run.sh` for a clean synthetic test, or pass the path to a private Compose copy. The runner temporarily permits UE/N6 traffic only within the isolated N6 bridge and removes those rules on exit. `results/acceptance.json` records the checks. Create `tests/lab/webui.env` before starting manually. Start the lab database, optionally restore a private copy of the open5gs database, then load `tests/lab/seed.js` into that lab database only. Start the core, then the `sim` profile. Never run the seed script against production.

The UPF fixture preserves the production custom behavior: three ogstun routes, N3 MTU 1600, and removal of UE MASQUERADE. The N6 test namespace has routes back through UPF. Its `n6-server.py` supplies lab-only DNS and HTTP responses; launch it using `nsenter -t <n6-container-pid> -n python3 tests/lab/n6-server.py`. Validate each UE's allocated subnet, DNS, HTTP, uplink and downlink ICMP. This is simulator acceptance; physical RAN and MPTCP validation remain separate.

## Production cutover

The host scripts deliberately target `/opt/priv5g/ncore` and existing `ncore_db_data` / `ncore_db_config` volumes. They are not general-purpose installers.

1. Complete isolated acceptance, export/import all eleven verified images, compare their IDs with `artifacts/images.json`.
2. Copy `host-upgrade.py`, `host-rollback.py` and the image manifest to a private staging directory on the host.
3. In an authorized maintenance window, run `python3 host-upgrade.py images.json`. It snapshots configuration/state, arms a 20-minute rollback timer, stops `priv5g-core`, backs up the stopped MongoDB volumes, updates only the Open5GS image references/version and WebUI secret mount, then starts the core.
4. The original Docker networks, volume names, MongoDB version, VPN/MPTCP, control interfaces and unrelated applications are preserved. The existing core unit temporarily stops its N6/monitoring containers as part of the core restart.
5. Validate actual versions, NRF/PFCP, original subscriptions/accounts, gNB reconnect, UE sessions, DNS and two-way traffic. If original test UE service is not recovered within ten minutes after startup, roll back.
6. Only after acceptance, create `COMMITTED` inside the printed backup directory and stop `open5gs-v280-rollback.timer`. Observe for 30 minutes.

Rollback: `python3 <backup>/host-rollback.py <backup>`. After commitment, use `--force` only for an intentional manual rollback. It explicitly stops containers even when the systemd start failed, saves the failed database state, restores pre-cutover database/configuration, and starts the old version. This restores data to the cutover snapshot; it does not merge later edits.

The WebUI .env mount preserves generated session/JWT keys across recreations. Login sessions can be invalidated by this version change; user accounts are retained. No additional public API or UE-IP query feature is introduced.

The Dockerfiles explicitly preserve executable entrypoints, and `.gitattributes` enforces Unix script line endings for Windows clones.

`host-check.py <private-output-dir>` captures a baseline/after snapshot. `host-accept.py <before-dir> <after-dir> <images.json> [explicitly-excluded-imsi ...]` compares the deployment. UE exclusions require an explicit operator/user decision and must be recorded alongside acceptance; they are never inferred automatically. `host-observe.py <output-dir> [seconds]` performs bounded read-only observation.
