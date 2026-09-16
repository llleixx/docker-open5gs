#!/bin/bash

# Keep the image-provided Open5GS interface setup, then make UE pools routed
# instead of masqueraded. This private core uses explicit Service Net routes,
# so services should see real UE addresses.
cd /usr/local/bin
source /usr/local/bin/helper_functions.sh

: "${UPF_RAN_IP:?UPF_RAN_IP is required}"
: "${UPF_RAN_MTU:?UPF_RAN_MTU is required}"
: "${UE_POOL_ROUTES:?UE_POOL_ROUTES is required}"

setup_container_interfaces "$@"

upf_ran_ip=$UPF_RAN_IP
upf_ran_mtu=$UPF_RAN_MTU
upf_ran_iface=$(ip -o -4 addr show | awk -v ip="$upf_ran_ip" '$4 ~ "^" ip "/" {print $2; exit}')
if [[ -z "$upf_ran_iface" ]]; then
    echo "upf: no interface found for UPF_RAN_IP=$upf_ran_ip" >&2
    exit 1
fi
ip link set dev "$upf_ran_iface" mtu "$upf_ran_mtu"

ue_pool_routes=$UE_POOL_ROUTES
iptables -t nat -S POSTROUTING >/dev/null
for subnet in $ue_pool_routes; do
    while iptables -t nat -C POSTROUTING -s "$subnet" ! -o ogstun -j MASQUERADE 2>/dev/null; do
        iptables -t nat -D POSTROUTING -s "$subnet" ! -o ogstun -j MASQUERADE
    done
done

exec open5gs-upfd "$@"
