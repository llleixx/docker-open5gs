
# global build-time arguments for FROM statements
# (https://docs.docker.com/engine/reference/builder/#understand-how-arg-and-from-interact)

ARG UBUNTU_VERSION="jammy"

FROM ubuntu:${UBUNTU_VERSION}

# build-time arguments
ARG OPEN5GS_VERSION="v2.8.0"
ARG OPEN5GS_COMMIT="157f611a530e292e40ec50f9d23f0ef5d4fcd6a6"
ARG BUILD_JOBS=4
ARG UBUNTU_MIRROR=http://archive.ubuntu.com/ubuntu
ARG DEBIAN_FRONTEND="noninteractive"

# install dependencies
RUN sed -i "s|http://archive.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g; s|http://security.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g" /etc/apt/sources.list \
    && apt-get update && apt-get install python3-pip python3-setuptools python3-wheel ninja-build build-essential \
	flex bison git cmake libsctp-dev libgnutls28-dev libgcrypt-dev libssl-dev libmongoc-dev libbson-dev \
	libyaml-dev libnghttp2-dev libmicrohttpd-dev libcurl4-gnutls-dev libtins-dev libtalloc-dev meson libidn-dev -y

# clone the specific open5gs version
RUN git clone --depth 1 --branch=${OPEN5GS_VERSION} https://github.com/open5gs/open5gs \
    && test "$(git -C open5gs rev-parse HEAD)" = "${OPEN5GS_COMMIT}"

# install open5gs
RUN cd open5gs && meson build --prefix=`pwd`/install && ninja -j ${BUILD_JOBS} -C build \
    && cd build && ninja install
