#!/bin/bash

# Command 1: Broker
gnome-terminal --tab --title="Broker" -- bash -c "podman run --rm -it --network host ghcr.io/eclipse-kuksa/kuksa-databroker:latest --insecure; exec bash"

# Command 2: Zonal
gnome-terminal --tab --title="Zonal" -- bash -c "podman run --rm -it --net=host -e LOG_LEVEL=DEBUG -v $(pwd)/../vss_dbc.json:/config/vss_dbc.json:Z -v $(pwd)/../fake_candump.log:/config/candump.log:Z can-provider:latest --val2dbc --dbc2val --use-socketcan; exec bash"

# Command 3: Broker CLI
gnome-terminal --tab --title="Broker CLI" -- bash -c "podman run --rm -it --network host ghcr.io/eclipse-kuksa/kuksa-databroker-cli:latest --server 127.0.0.1:55555; exec bash"
