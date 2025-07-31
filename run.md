sudo podman run --rm -it --net=host --privileged -e LOG_LEVEL=DEBUG -v $(pwd)/vss_dbc.json:/config/vss_dbc.json:Z hr_zonal:latest --val2dbc --dbc2val --server-type kuksa_databroker
