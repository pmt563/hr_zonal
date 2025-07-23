#!/bin/bash

#       CREATE VIRTUAL CAN
########################################################################
# Copyright (c) 2020 Robert Bosch GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
########################################################################

#
# Set up virtual can device "elmcan" as sink
# for the elm2canbridge
#

#Default dev, can be overridden by commandline
DEV=elmcan

if [ -n "$1" ]
then
    DEV=$1
fi

echo "createvcan: Preparing to bring up vcan interface $DEV"

virtualCanConfigure() {
	echo "createvcan: Setting up VIRTUAL CAN"
	sudo  modprobe -n --first-time vcan &> /dev/null
	loadmod=$?
	if [ $loadmod -eq 0 ]
	then
		echo "createvcan: Virtual CAN module not yet loaded. Loading......"
		sudo modprobe vcan
	fi


	ifconfig "$DEV" &> /dev/null
	noif=$?
	if [ $noif -eq 1 ]
	then
		echo "createvcan: Virtual CAN interface not yet existing. Creating..."
		sudo ip link add dev "$DEV" type vcan
	fi
	sudo ip link set "$DEV" up
}



#If up?
up=$(ifconfig "$DEV" 2> /dev/null | grep NOARP | grep -c RUNNING)

if [ $up -eq 1 ]
then
   echo "createvcan: Interface already up. Exiting"
   exit
fi

virtualCanConfigure

echo "createvcan: Done."


#  Create the terminal to monitor CAN node
gnome-terminal --tab --title="CAN_monitor" -- bash -c "candump vcan0"
echo "Created tab to monitor CAN node!"

# Create new terminal to replay CANdump file
cd /home/kali/tuan_dz/dev_veh-app_learning/debugging_container/provider/kcan_provider/kuksa-can-provider
gnome-terminal --tab --title="Reader" -- bash -c "source venv/bin/activate"
echo "Activated virtual environment!"
python replay_candump.py -I /home/kali/tuan_dz/dev_veh-app_learning/debugging_container/provider/kcan_provider/kuksa-can-provider/fake_candump.log -c vcan0 -s elmcan -g 100 -l -v
echo "Replaying CAN message in CANdump.log..."