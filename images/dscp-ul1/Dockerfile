ARG RUNTIME_BASE
FROM base-open5gs:v2.8.0-r1-dscp-ul1 AS builder
FROM ${RUNTIME_BASE}
ARG NF
COPY --from=builder /open5gs/install/bin/open5gs-${NF}d /usr/local/bin/
COPY --from=builder /open5gs/install/lib/x86_64-linux-gnu/*.so* /usr/local/lib/
RUN ldconfig
