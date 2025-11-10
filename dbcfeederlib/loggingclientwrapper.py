#!/usr/bin/env python3

#################################################################################
# Copyright (c) 2023 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License 2.0 which is available at
# http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#################################################################################

import logging
from typing import Any, List, Optional
from .clientwrapper import ClientWrapper

log = logging.getLogger(__name__)


class LoggingClientWrapper(ClientWrapper):
    def __init__(self, ip: str = "127.0.0.1", port: int = 55555, token_path: str = "", tls: bool = True):
        super().__init__(ip, port, token_path, tls)
        self._connected = True  
        self._registered = True  
        self._subscription_callback = None
        self._subscribed_signals = []

    def _do_init(self):
        log.info("[Initializing] Logging Client Wrapper")

    def start(self):
        log.info("[Starting] Logging Client Wrapper")
        return True

    def stop(self):
        log.info("[Stopping] Logging Client Wrapper")
    def is_connected(self) -> bool:
        return self._connected

    def is_signal_defined(self, vss_name: str) -> bool:
        log.debug("[Checking] if signal %s is defined - assuming True for logging", vss_name)
        return True

    def update_datapoint(self, name: str, value: Any) -> bool:
        log.info("[Updating] VSS DataPoint - Signal: %s, Value: %s (%s)", name, value, type(value).__name__)
        return True

    def supports_subscription(self) -> bool:
        return True

    async def subscribe(self, vss_names: List[str], callback):

        self._subscription_callback = callback
        self._subscribed_signals = vss_names
        
        log.info("[Subscribed] to VSS signals: %s", vss_names)
        
        
        return True
