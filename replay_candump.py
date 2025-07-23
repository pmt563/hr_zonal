import can
import time
import re
import argparse

def parse_candump_line(line):
    """Parse a candump log line and extract timestamp, interface, arbitration_id, and data."""
    # Example candump format: (1234567890.123456) elmcan 123#1122334455667788
    pattern = r'\((\d+\.\d+)\)\s+(\w+)\s+([0-9A-F]+)#([0-9A-F]*)'
    match = re.match(pattern, line.strip())
    if not match:
        return None
    timestamp, interface, arb_id, data = match.groups()
    arb_id = int(arb_id, 16)
    data = bytes.fromhex(data) if data else b''
    return float(timestamp), interface, arb_id, data

def replay_can_messages(log_file, interface='vcan0', src_interface='elmcan', gap_ms=100, loop_indefinitely=False, verbose=False):
    """Replay CAN messages from a candump log file to the specified interface."""
    # Initialize CAN bus
    bus = None
    try:
        bus = can.interface.Bus(channel=interface, interface='socketcan')  # Updated to use 'interface' instead of 'bustype'
    except can.CanError as e:
        print(f"Failed to initialize CAN bus on {interface}: {e}")
        return

    gap_s = gap_ms / 1000.0  # Convert gap from milliseconds to seconds

    try:
        while True:
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        parsed = parse_candump_line(line)
                        if parsed is None:
                            continue
                        timestamp, log_interface, arb_id, data = parsed

                        # Only replay messages from the specified source interface
                        if log_interface != src_interface:
                            continue

                        # Create and send CAN message
                        msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=(arb_id > 0x7FF))
                        try:
                            bus.send(msg)
                            if verbose:
                                print(f"Sent: {interface} {arb_id:X}#{data.hex().upper()}")
                        except can.CanError as e:
                            print(f"Failed to send message: {e}")

                        # Respect the gap between messages
                        time.sleep(gap_s)

            except FileNotFoundError:
                print(f"Log file {log_file} not found.")
                return
            except Exception as e:
                print(f"Error during replay: {e}")
                return

            if not loop_indefinitely:
                break

    finally:
        if bus is not None:
            try:
                bus.shutdown()
                print("CAN bus shut down properly.")
            except Exception as e:
                print(f"Error shutting down CAN bus: {e}")

def main():
    parser = argparse.ArgumentParser(description="Replay CAN messages from a candump log file.")
    parser.add_argument('-I', '--input-file', required=True, help="Path to the candump log file")
    parser.add_argument('-c', '--channel', default='vcan0', help="CAN interface to send messages to (default: vcan0)")
    parser.add_argument('-s', '--src-interface', default='elmcan', help="Source interface in log to replay (default: elmcan)")
    parser.add_argument('-g', '--gap', type=int, default=300, help="Gap between messages in milliseconds (default: 100)")
    parser.add_argument('-l', '--loop', action='store_true', help="Loop indefinitely")
    parser.add_argument('-v', '--verbose', action='store_true', help="Print sent messages")

    args = parser.parse_args()

    replay_can_messages(
        log_file=args.input_file,
        interface=args.channel,
        src_interface=args.src_interface,
        gap_ms=args.gap,
        loop_indefinitely=args.loop,
        verbose=args.verbose
    )

if __name__ == "__main__":
    main()
