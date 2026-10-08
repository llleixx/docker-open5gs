# DSCP experiment scripts

Read ../../docs/dscp-ul1.md and the field report before executing.

- trial.py: guarded backup, single-bridge apply and rollback. Fixed paths target /opt/priv5g/qos-ul1/trial and /opt/priv5g/ncore. Do not overwrite the existing snapshot. Use a new explicitly configured directory for a new trial; prepare refuses an existing snapshot.
- make_policy.py: copy subscription defaults; exact SUPI/slice/DNN scope; optional TCP 12166 probe. Never substitute an example subscription.
- stage_a.py and tcp_probe.py: original-core port-only checks.
- switch_vpn.py and correlate.py: bridge8 VPN switching and unique USB/N3 packet correlation. The former restores priority/prefer in finally and assumes the existing hzepics8 fixture.
- probe_matrix.py: source-bound TCP marking and wrong-port checks. TCP may clear requested ECN bits; inspect packets rather than counting requests as coverage.
- invalid_config_lab.py: network-isolated PCF rejection cases.
- check_lab_nas.py: synthetic lab NAS precedence regression.
- lifecycle_lab.py and check_lifecycle.py: synthetic SBI updates and N4 wire assertions. The last data-plane regression failed; do not suppress it or describe the whole test as passed. setup.pcap is cached for retry against the same sessions; use a new results/lifecycle directory for a new fixture.
- competition.py, loadtest.py and gnb_pm.py: incomplete field acceptance tooling. Same-cell gate stops before load. PM collector requires BS-02. Full execution, receiver throughput, transport bottleneck checks and real VPN competition statistics remain outstanding.
- recover_links.py may restart modems on unreachable bridges. Use only during maintenance, not as a read-only health check. CLI exit zero alone does not prove an AT restart succeeded.
- final_audit.py: post-rollback evidence.

No script disables NAS security. Failed-candidate evidence is retained separately. No automatic wider rollout is implemented.
