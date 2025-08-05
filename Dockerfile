
# /********************************************************************************
# * Copyright (c) 2022 Contributors to the Eclipse Foundation
# *
# * See the NOTICE file(s) distributed with this work for additional
# * information regarding copyright ownership.
# *
# * This program and the accompanying materials are made available under the
# * terms of the Apache License 2.0 which is available at
# * http://www.apache.org/licenses/LICENSE-2.0
# *
# * SPDX-License-Identifier: Apache-2.0
# ********************************************************************************/

# Build stage, to create a Virtual Environment
FROM python:3.10-slim-bookworm AS builder

ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN echo "-- Running on $BUILDPLATFORM, building for $TARGETPLATFORM"

# Install dependencies needed for building, including libc6 for dynamic linker
RUN apt-get update && apt-get install -y \
    binutils \
    git \
    gcc \
    libc6 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade --no-cache-dir pip build pyinstaller

COPY requirements.txt /

RUN pip install --no-cache-dir -r requirements.txt

# Copy files after dependencies to leverage caching
COPY . /
COPY ./dbcfeederlib/libcontrolcanfd.so ./dbcfeederlib/libcontrolcanfd.so

# By default, use certificates and tokens from kuksa_client
RUN pyinstaller --collect-data kuksa_client --hidden-import can.interfaces.socketcan --add-binary ./dbcfeederlib/libcontrolcanfd.so:dbcfeederlib --clean -F -s dbcfeeder.py

WORKDIR /dist

WORKDIR /data
COPY ./config/* ./config/
COPY ./mapping/ ./mapping/
COPY ./*.dbc ./candump*.log ./*.json ./
COPY ./HRN.dbc ./HRN.dbc

# Prepare dynamic linker in a known location
RUN ld_path=$(find / -name ld-linux-aarch64.so.1 2>/dev/null | head -n 1) && \
    if [ -n "$ld_path" ]; then cp "$ld_path" /dist/ld-linux-aarch64.so.1; else exit 1; fi

# Use distroless base image for runtime
FROM gcr.io/distroless/base-debian12

WORKDIR /dist

# Copy built artifacts and data
COPY --from=builder /dist/* .
COPY --from=builder /data/ ./

# Copy required libraries
COPY --from=builder /usr/lib/aarch64-linux-gnu/libz.so.1 /lib/
COPY --from=builder /usr/lib/aarch64-linux-gnu/libstdc++.so.6 /lib/
COPY --from=builder /usr/lib/aarch64-linux-gnu/libgcc_s.so.1 /lib/
COPY --from=builder /usr/lib/aarch64-linux-gnu/libc.so.6 /lib/
COPY --from=builder /usr/lib/aarch64-linux-gnu/libm.so.6 /lib/
COPY --from=builder /dist/ld-linux-aarch64.so.1 /lib/

ENV PATH="/dist:$PATH"

# Useful dumps about feeding values
ENV LOG_LEVEL="info"

# Vehicle Data Broker host:port
ENV VDB_ADDRESS="localhost:55555"
ENV VEHICLEDATABROKER_DAPR_APP_ID=vehicledatabroker

ENV PYTHONUNBUFFERED=yes

ENTRYPOINT ["./dbcfeeder"]


