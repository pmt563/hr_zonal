				BROKER CLI
podman run --rm -it --network kuksa \
ghcr.io/eclipse-kuksa/kuksa-databroker-cli:latest \
--server HnR:55555 

actuate Vehicle.Powertrain.Transmission.IsElectricalPowertrainEngaged true
actuate Vehicle.Powertrain.Transmission.IsLowRangeEngaged true

				ZONAL
podman run --rm -it --device=/dev/bus/usb/001/004 --group-add keep-groups --network kuksa -e LOG_LEVEL=DEBUG -v $(pwd)/vss_dbc.json:/config/vss_dbc.json:Z hr_zonal:latest --val2dbc --dbc2val --server-type kuksa_databroker
