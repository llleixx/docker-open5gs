
# global build-time arguments for FROM statements
ARG NODE_VERSION="20"

ARG NODE_BUILD_IMAGE=node:20-bookworm
ARG NODE_RUNTIME_IMAGE=node:20-bookworm-slim

FROM ${NODE_BUILD_IMAGE} AS builder

# build-time arguments for builder
ARG OPEN5GS_VERSION="v2.8.0"
ARG OPEN5GS_COMMIT="157f611a530e292e40ec50f9d23f0ef5d4fcd6a6"
ARG DEBIAN_FRONTEND="noninteractive"

# install dependencies
RUN apt-get update && apt-get install git -y

# clone the specific open5gs version
RUN git clone --depth 1 --branch=${OPEN5GS_VERSION} https://github.com/open5gs/open5gs \
    && test "$(git -C open5gs rev-parse HEAD)" = "${OPEN5GS_COMMIT}"

# install webui
RUN cd open5gs/webui && npm ci && npm run build

FROM ${NODE_RUNTIME_IMAGE}

# copy webui
COPY --from=builder /open5gs/webui/ /usr/local/src/webui

ENV DB_URI="mongodb://localhost/open5gs"
ENV HOSTNAME="0.0.0.0"
ENV PORT=9999
ENV NODE_ENV="dev"

WORKDIR /usr/local/src/webui
ENTRYPOINT ["npm"]

# use CMD to provide arguments to ENTRYPOINT (can be overridden by user)
CMD [ "run", "dev" ]
