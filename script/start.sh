#!/bin/bash

# Copyright (c) 2020 Robert Bosch GmbH
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0

# Default virtual CAN device
DEV=vcan0

manage_vcan0() 
{
    echo "createvcan: Preparing to manage vcan interface $DEV"

    # Check if vcan0 exists and bring it down if it does
    if ip link show "$DEV" &> /dev/null; then
        echo "createvcan: $DEV exists, bringing it down..."
        sudo ip link set "$DEV" down
        if [ $? -eq 0 ]; then
            echo "createvcan: $DEV successfully brought down."
        else
            echo "createvcan: Failed to bring down $DEV."
            exit 1
        fi
    else
        echo "createvcan: $DEV does not exist, no need to bring down."
    fi

    sudo modprobe -n --first-time vcan &> /dev/null
    loadmod=$?
    if [ $loadmod -eq 0 ]; then
        echo "createvcan: Virtual CAN module not yet loaded. Loading..."
        sudo modprobe vcan
        if [ $? -ne 0 ]; then
            echo "createvcan: Failed to load vcan module."
            exit 1
        fi
    fi

    if ! ip link show "$DEV" &> /dev/null; then
        echo "createvcan: Virtual CAN interface not yet existing. Creating..."
        sudo ip link add dev "$DEV" type vcan
        if [ $? -ne 0 ]; then
            echo "createvcan: Failed to create $DEV."
            exit 1
        fi
    fi

    echo "createvcan: Bringing up $DEV..."
    sudo ip link set "$DEV" up
    if [ $? -eq 0 ]; then
        echo "createvcan: $DEV successfully brought up."
    else
        echo "createvcan: Failed to bring up $DEV."
        exit 1
    fi
}

manage_vcan0

CAN_PROVIDER_DIR="/home/kali/tuan_dz/dev_veh-app_learning/debugging_container/provider/kcan_provider/kuksa-can-provider"
if [ ! -d "$CAN_PROVIDER_DIR" ]; then
    echo "Error: Directory $CAN_PROVIDER_DIR does not exist."
    exit 1
fi
cd "$CAN_PROVIDER_DIR" || exit 1

# Run all processes in separate gnome-terminal tabs
# Tab 1: CAN Monitor (candump)
gnome-terminal --tab --title="CAN_monitor" -- bash -c "candump vcan0; exec bash"
echo "Created tab to monitor CAN node!"

# Tab 2: CAN Replay
gnome-terminal --tab --title="Reader" -- bash -c "source venv/bin/activate && python replay_candump.py -I fake_enum_candump.log -c vcan0 -s elmcan -g 100 -l -v; exec bash"
echo "Replaying CAN message in fake_candump.log..."

# Tab 3: Broker
gnome-terminal --tab --title="Broker" -- bash -c "podman run --rm -it --network host ghcr.io/eclipse-kuksa/kuksa-databroker:latest --insecure; exec bash"

# Tab 4: Zonal
gnome-terminal --tab --title="Zonal" -- bash -c "podman run --rm -it --net=host -e LOG_LEVEL=DEBUG -v $(pwd)/vss_dbc.json:/config/vss_dbc.json:Z can-provider:latest --val2dbc --dbc2val --use-socketcan; exec bash"

# Tab 5: Broker CLI
gnome-terminal --tab --title="Broker CLI" -- bash -c "sleep 3 && podman run --rm -it --network host ghcr.io/eclipse-kuksa/kuksa-databroker-cli:latest --server 127.0.0.1:55555; exec bash"

echo "All processes started in separate terminal tabs."
