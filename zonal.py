''' CONFIGURATION NOTE
Permissions: Ensure the program has sufficient permissions to access can0. This is typically not an issue with vcan0 since it's virtual, 
but physical interfaces may require root privileges or specific permissions.
    --> network: host
        option: privileges

Ensure can0 is available and properly configured:
    ip link show 
    ifconfig

CAN bitrate
    sudo ip link set can0 up type can bitrate 500000
'''

import argparse
import configparser
import logging
import os
import queue
import sys
import threading
import time
from signal import SIGINT, SIGTERM, signal
from typing import Any, Dict, List, Optional

from dbcfeederlib.canclient import CANClient
from dbcfeederlib.canreader import CanReader
from dbcfeederlib import dbc2vssmapper
from dbcfeederlib import dbcreader
from dbcfeederlib import j1939reader
from dbcfeederlib import elm2canbridge

log = logging.getLogger("dbcfeeder")

CONFIG_SECTION_CAN = "can"
CONFIG_SECTION_ELMCAN = "elmcan"
CONFIG_SECTION_GENERAL = "general"

CONFIG_OPTION_CAN_DUMP_FILE = "candumpfile"
CONFIG_OPTION_DBC_DEFAULT_FILE = "dbc_default_file"
CONFIG_OPTION_MAPPING = "mapping"
CONFIG_OPTION_PORT = "port"
CONFIG_OPTION_J1939 = "j1939"
CONFIG_OPTION_PHYSICAL_CAN = "use_physical_can"
CAN_PORT = "port"

class Feeder:

    def __init__(self, output_file: Optional[str] = None, dbc2vss: bool = True, vss2dbc: bool = False):
        self._running: bool = False
        self._reader: Optional[CanReader] = None
        self._mapper: Optional[dbc2vssmapper.Mapper] = None
        self._dbc2vss_queue: queue.Queue[dbc2vssmapper.VSSObservation] = queue.Queue()
        self._output_file = output_file
        self._elmcan_config: Dict[str, Any] = {}
        self._dbc2vss_enabled = dbc2vss
        self._vss2dbc_enabled = vss2dbc
        self._canclient: Optional[CANClient] = None
        self._transmit: bool = False

    def start(
        self,
        canport: str,
        can_fd: bool,
        dbc_file_names: List[str],
        mappingfile: str,
        dbc_default_file: Optional[str],
        candumpfile: Optional[str],
        use_j1939: bool = False,
        use_strict_parsing: bool = False,
        use_physical_can: bool = False
    ):
        self._running = True
        self._mapper = dbc2vssmapper.Mapper(
            mapping_definitions_file=mappingfile,
            dbc_file_names=dbc_file_names,
            use_strict_parsing=use_strict_parsing,
            expect_extended_frame_ids=use_j1939,
            can_signal_default_values_file=dbc_default_file)

        threads = []

        if not self._dbc2vss_enabled:
            log.info("Mapping of CAN signals to VSS Data Entries is disabled.")
        elif not self._mapper.has_dbc2vss_mapping():
            log.info("No mappings from CAN signals to VSS Data Entries defined.")
        else:
            log.info("Setting up reception of CAN signals")
            if use_j1939:
                log.info("Using J1939 reader")
                self._reader = j1939reader.J1939Reader(self._dbc2vss_queue, self._mapper, canport, candumpfile)
            else:
                log.info("Using DBC reader")
                self._reader = dbcreader.DBCReader(self._dbc2vss_queue, self._mapper, canport, can_fd, candumpfile)

            if use_physical_can:
                log.info("Using physical CAN hardware for input messages")
                if candumpfile:
                    log.warning("Ignoring candumpfile since physical CAN hardware is enabled")
                    candumpfile = None
                if canport == 'elmcan':
                    log.error("Cannot use elmcan with physical CAN hardware!")
                    self.stop()
                    return

            if canport == 'elmcan' and not use_physical_can:
                log.info("Using elmcan. Trying to set up elm2can bridge")
                whitelisted_frame_ids: List[int] = []
                for filter in self._mapper.can_frame_id_whitelist():
                    whitelisted_frame_ids.append(filter.can_id)
                elm2canbridge.elm2canbridge(canport, self._elmcan_config, whitelisted_frame_ids)

            self._reader.start()

            receiver = threading.Thread(target=self._run_receiver)
            receiver.start()
            threads.append(receiver)

        if self._vss2dbc_enabled:
            log.warning("VSS to DBC mapping is not supported in this non-gRPC version.")
            self.stop()

        for thread in threads:
            thread.join()

    def stop(self):
        log.info("Shutting down...")
        self._running = False
        if self._reader is not None:
            self._reader.stop()
        if self._canclient:
            self._canclient.stop()
        self._transmit = False

    def is_running(self) -> bool:
        return self._running

    def _run_receiver(self):
        processing_started = False
        messages_processed = 0
        last_sent_log_entry = 0
        queue_max_size = 0
        output = sys.stdout
        if self._output_file:
            output = open(self._output_file, 'a', encoding='utf-8')

        try:
            while self._running:
                try:
                    if not processing_started:
                        processing_started = True
                        log.info("Starting to process CAN signals")
                    queue_size = self._dbc2vss_queue.qsize()
                    if queue_size > queue_max_size:
                        queue_max_size = queue_size
                    vss_observation = self._dbc2vss_queue.get(timeout=1)
                    vss_mapping = self._mapper.get_dbc2vss_mapping(vss_observation.dbc_name, vss_observation.vss_name)
                    value = vss_mapping.transform_value(vss_observation.raw_value)
                    if value is None:
                        log.warning(
                            "Value ignored for dbc %s to VSS %s, from raw value %s of type %s",
                            vss_observation.dbc_name, vss_observation.vss_name, vss_observation.raw_value, type(vss_observation.raw_value)
                        )
                    elif not vss_mapping.change_condition_fulfilled(value):
                        log.debug("Value condition not fulfilled for VSS %s, value %s", vss_observation.vss_name, value)
                    else:
                        output.write(f"Datapoint({vss_observation.vss_name}, {value}, {vss_observation.time})\n")
                        output.flush()
                        log.debug("Processed DataPoint(%s, %s, %f)", vss_observation.vss_name, value, vss_observation.time)
                        messages_processed += 1
                        if messages_processed >= (2 * last_sent_log_entry):
                            log.info(
                                "Processed %d CAN messages, maximum queue size: %d",
                                messages_processed, queue_max_size
                            )
                            last_sent_log_entry = messages_processed
                except queue.Empty:
                    pass
                except Exception as e:
                    log.error("Exception caught in main loop: %s", e, exc_info=True)
        finally:
            if self._output_file and output != sys.stdout:
                output.close()

def _parse_config(filename: str) -> configparser.ConfigParser:
    configfile = None
    if filename:
        if not os.path.exists(filename):
            log.warning("Couldn't find config file %s", filename)
            raise FileNotFoundError(os.strerror(os.errno.ENOENT), filename)
        configfile = filename
    else:
        config_candidates = [
            "/config/dbc_feeder.ini",
            "/etc/dbc_feeder.ini",
            "config/dbc_feeder.ini",
        ]
        for candidate in config_candidates:
            if os.path.isfile(candidate):
                configfile = candidate
                break

    config = configparser.ConfigParser()
    log.info("Reading configuration from file: %s", configfile)
    if configfile:
        config.read(configfile)
    return config

def _get_command_line_args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="dbcfeeder (non-gRPC version)")
    parser.add_argument("--config", metavar="FILE", help="The file to read configuration properties from")
    parser.add_argument(
        "--dbcfile", metavar="FILE", help="A (comma-separated) list of DBC files to read message definitions from."
    )
    parser.add_argument(
        "--dumpfile", metavar="FILE", help="Replay recorded CAN traffic from dumpfile"
    )
    parser.add_argument("--canport", metavar="DEVICE", help="The name of the device representing the CAN bus")
    parser.add_argument("--use-j1939", action="store_true", help="Use J1939 messages on the CAN bus")
    parser.add_argument(
        "--use-socketcan",
        action="store_true",
        help="Use SocketCAN (overriding any use of --dumpfile)",
    )
    parser.add_argument(
        '--canfd',
        action='store_true',
        help="Open bus interface in CAN-FD mode"
    )
    parser.add_argument(
        "--mapping",
        metavar="FILE",
        help="The file to read definitions for mapping CAN signals to VSS datapoints from",
    )
    parser.add_argument(
        "--dbc-default",
        metavar="FILE",
        help="A file containing default values for DBC signals.",
    )
    parser.add_argument(
        "--output-file",
        metavar="FILE",
        help="File to write VSS datapoints to (defaults to console if not specified)",
    )
    parser.add_argument(
        "--lax-dbc-parsing",
        dest="strict",
        action="store_false",
        help="Disable strict parsing of DBC files.",
    )
    parser.add_argument('--dbc2val', action='store_true', help="Monitor CAN and map signals to VSS")
    parser.add_argument('--no-dbc2val', action='store_true', help="Do not monitor signals on CAN")
    parser.add_argument(
        "--use-physical-can",
        action="store_true",
        help="Use physical CAN hardware to receive input messages from the CAN network",
    )
    return parser

def main(argv):
    parser = _get_command_line_args_parser()
    args = parser.parse_args()
    config = _parse_config(args.config)

    if args.dbc2val:
        use_dbc2val = True
    elif args.no_dbc2val:
        use_dbc2val = False
    else:
        use_dbc2val = config.getboolean(CONFIG_SECTION_GENERAL, "dbc2val", fallback=True)
    log.info("DBC2VAL mode is: %s", use_dbc2val)

    if args.dbcfile:
        dbcfile = args.dbcfile
    elif os.environ.get("DBC_FILE"):
        dbcfile = os.environ.get("DBC_FILE")
    else:
        dbcfile = config.get(CONFIG_SECTION_CAN, "dbcfile", fallback=None)

    if not dbcfile:
        parser.error("No DBC file(s) specified")

    if args.canport:
        canport = args.canport
    elif os.environ.get("CAN_PORT"):
        canport = os.environ.get("CAN_PORT")
    else:
        canport = config.get(CONFIG_SECTION_CAN, CONFIG_OPTION_PORT, fallback=None)

    if not canport:
        parser.error("No CAN port specified")

    if args.dbc_default:
        dbc_default = args.dbc_default
    elif os.environ.get("DBC_DEFAULT_FILE"):
        dbc_default = os.environ.get("DBC_DEFAULT_FILE")
    else:
        dbc_default = config.get(CONFIG_SECTION_CAN, CONFIG_OPTION_DBC_DEFAULT_FILE, fallback="dbc_default_values.json")

    if args.mapping:
        mappingfile = args.mapping
    elif os.environ.get("MAPPING_FILE"):
        mappingfile = os.environ.get("MAPPING_FILE")
    else:
        mappingfile = config.get(CONFIG_SECTION_GENERAL, CONFIG_OPTION_MAPPING, fallback="mapping/vss_4.0/vss_dbc.json")

    if args.use_j1939:
        use_j1939 = True
    elif os.environ.get("USE_J1939"):
        use_j1939 = True
    else:
        use_j1939 = config.getboolean(CONFIG_SECTION_CAN, CONFIG_OPTION_J1939, fallback=False)

    if args.use_physical_can:
        use_physical_can = True
    elif os.environ.get("USE_PHYSICAL_CAN"):
        use_physical_can = os.environ.get("USE_PHYSICAL_CAN").lower() in ('true', '1', 'yes')
    else:
        use_physical_can = config.getboolean(CONFIG_SECTION_CAN, CONFIG_OPTION_PHYSICAL_CAN, fallback=False)
    log.info("Physical CAN hardware mode is: %s", use_physical_can)

    candumpfile = None
    if not args.use_socketcan and not use_physical_can:
        if args.dumpfile:
            candumpfile = args.dumpfile
        elif os.environ.get("CANDUMP_FILE"):
            candumpfile = os.environ.get("CANDUMP_FILE")
        else:
            candumpfile = config.get(CONFIG_SECTION_CAN, CONFIG_OPTION_CAN_DUMP_FILE, fallback=None)

    elmcan_config = {}
    if canport == "elmcan":
        if candumpfile is not None:
            parser.error("It is a contradiction specifying both elmcan and candumpfile!")
        if use_physical_can:
            parser.error("It is a contradiction specifying both elmcan and use-physical-can!")
        if not config.has_section(CONFIG_SECTION_ELMCAN):
            parser.error("Cannot use elmcan without configuration in [elmcan] section!")
        elmcan_config = config[CONFIG_SECTION_ELMCAN]

    feeder = Feeder(output_file=args.output_file, dbc2vss=use_dbc2val, vss2dbc=False)

    def signal_handler(signal_received, *_):
        log.info("Received signal %s, stopping...", signal_received)
        if not feeder.is_running():
            log.warning("Shutting down now!")
            sys.exit(-1)
        feeder.stop()

    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)

    log.info("Starting CAN feeder")
    feeder.start(
        canport=canport,
        dbc_file_names=dbcfile.split(','),
        mappingfile=mappingfile,
        dbc_default_file=dbc_default,
        candumpfile=candumpfile,
        use_j1939=use_j1939,
        use_strict_parsing=args.strict,
        can_fd=args.canfd,
        use_physical_can=use_physical_can  
    )

    return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv))