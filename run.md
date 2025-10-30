#!/bin/bash

DEVICE_ID="8087:0026"

DEVICE_INFO=$(lsusb | grep "$DEVICE_ID")

if [ -z "$DEVICE_INFO" ]; then
    echo "Not found device: $DEVICE_ID"
    exit 1
fi

BUS=$(echo "$DEVICE_INFO" | awk '{print $2}' | sed 's/^0*//')
DEVICE_NUM=$(echo "$DEVICE_INFO" | awk '{print $4}' | sed 's/://' | sed 's/^0*//')

DEVICE_PATH="/dev/bus/usb/$BUS/$DEVICE_NUM"

if [ ! -e "$DEVICE_PATH" ]; then
    echo "Error: Device path not found $DEVICE_PATH"
    exit 1
fi

echo "Grantting permissions 777 for device: $DEVICE_PATH"
sudo chmod 777 "$DEVICE_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Successfully granted permissions for $DEVICE_PATH"
else
    echo "❌ Error granting permissions"
    exit 1
fi

# Run container
echo "🚀 Starting container..."
podman run --rm -it \
    --device="$DEVICE_PATH" \
    --group-add keep-groups \
    --network host \
    -e LOG_LEVEL=DEBUG \
    -v "$(pwd)/vss_dbc.json:/config/vss_dbc.json:Z" \
    hr_zonal:latest \
    --val2dbc --dbc2val --server-type kuksa_databroker

if [ $? -eq 0 ]; then
    echo "✅ Successfully started container Podman"
else
    echo "❌ Error starting container Podman"
    exit 1
fi
