# Uplink DSCP candidate (2026-10-08)

Status: operator authorized enabling the verified build after the initial trial rollback. The current deployment policy covers all present/future SUPIs served by PLMN 460/88, with DSCP-only uplink filters in slice1. Three-bridge performance acceptance is still outstanding, and dynamic-policy simulator data-plane regression remains unsuccessful; ordinary DSCP switching does not dynamically change policies.

## Build

Run bash scripts/build-dscp-ul1.sh at repository root. This checks the immutable original compiler/runtime image IDs in release-dscp-ul1.lock.json, verifies Open5GS commit 157f611a530e292e40ec50f9d23f0ef5d4fcd6a6, applies images/base-open5gs/patches/dscp-ul1.patch, builds, runs Meson unit suites and exports three patched images. The build uses --network none; original images must already exist. No r1 tag is overwritten.

Outputs in artifacts/dscp-ul1: build.log, images.json, SHA256SUMS, open5gs-v2.8.0-r1-dscp-ul1.tar.gz. Image IDs are config digests; these local images have not been pushed and have no registry manifest digest. Input reproducibility does not imply byte-identical timestamped image metadata. The source commit and exact patch correspondence are recorded in source-dscp-ul1.json. The image build predates the Git commit; the code delta is identical.

## Policy

Optional flow field tos_traffic_class: "b8fc" is encoded as standard SBI tosTrafficClass. Four hex digits and nonzero mask are required. 68fc selects DSCP 26; ECN bits are ignored by mask fc. The initial trial used exact SUPIs and TCP 12165/12166. The operator subsequently removed those restrictions. scripts/dscp-global-policy.py verifies uniform subscription defaults and builds one PLMN-wide policy, adding DSCP-only rules to S-NSSAI 1/000001 and DNN slice1 with flow description permit out ip from any to assigned. It retains all other known slices/DNNs because Open5GS local-policy selection does not fall back to the database when a matching PLMN policy lacks a DNN. Default QoS, AMBR and ARP are copied unchanged. Future subscribers use these common local-policy defaults; introducing per-subscriber overrides or new DNNs requires explicit policy changes. This does not bypass subscriber authentication or DNN authorization.

The patch carries the condition through policy copies, NAS component 0x70, PFCP TTC Create/Update PDR and IPv4/IPv6 UPF rule matching. Uplink-only empty downlink PDRs remain behind the default PDR. NAS precedence comes from the PCC rule, not that unused-direction PFCP fallback (65536 truncates to zero in an 8-bit NAS field).

## Validation

tests/dscp-ul1 holds actual experiment scripts. Integration scripts refer to the isolated fixture under private/dscp-ul1/lab; reproduce it from tests/lab with 10.250.80/81/82 transport/service subnets and 83/84/85 UE pools. They are not generic production test runners.

Passed: core/crypt/unit suites; ordinary three-slice registration and bidirectional data regression with/without policy; malformed PCF configuration rejection; SBI invalid-mask rejection and N4 lifecycle wire checks; real RM500U ten-cycle USB/N3 classification, VPN continuity, default downlink and reconnect recovery.

Not passed: full dynamic-policy simulated data-plane lifecycle (NGAP procedure 17 unhandled plus radio context failures); three-bridge same-cell/performance gate. IPv6 and ECN variants are unit-tested, not field-accepted. Competition scripts have not completed a field load test and do not establish bottleneck exclusion or performance acceptance.

Field evidence is in the Windows workspace reports/5g-dscp-ul1-20261008/实施与验证报告.md. Final patch SHA256: cc7aec461dc9a78f23acbaca84ae09e2e6c4b36e60fffcd8a54121070483897c.
