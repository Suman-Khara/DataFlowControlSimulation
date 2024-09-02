import sys
import socket
from stop_and_wait import Sender as StopAndWaitSender
from go_back_n import Sender as GoBackNSender

def main():
    # Ensure the correct number of command-line arguments
    if len(sys.argv) != 5:
        print("Usage: python sender.py <protocol> <file_path> <packet_size> <technique>")
        print("Protocol: 'StopAndWait' or '1', 'GoBackN' or '2'")
        print("Technique: 'CRC' or '1', 'Checksum' or '2'")
        sys.exit(1)

    # Extract command-line arguments
    protocol_input = sys.argv[1]
    file_path = sys.argv[2]
    packet_size = int(sys.argv[3])
    technique_input = sys.argv[4]

    # Define mappings for protocols and techniques
    protocol_map = {
        '1': 'StopAndWait',
        '2': 'GoBackN',
        'StopAndWait': 'StopAndWait',
        'GoBackN': 'GoBackN'
    }

    technique_map = {
        '1': 'CRC',
        '2': 'Checksum',
        'CRC': 'CRC',
        'Checksum': 'Checksum'
    }

    # Map protocol input to protocol name
    protocol = protocol_map.get(protocol_input)
    if not protocol:
        print("Error: Invalid protocol. Choose 'StopAndWait', 'GoBackN', '1', or '2'.")
        sys.exit(1)

    # Map technique input to technique name
    technique = technique_map.get(technique_input)
    if not technique:
        print("Error: Technique must be either 'CRC', 'Checksum', '1', or '2'.")
        sys.exit(1)

    # Hardcoded MAC addresses (example addresses)
    source_address = b'\x01\x02\x03\x04\x05\x06'
    destination_address = b'\x06\x05\x04\x03\x02\x01'

    # Determine the protocol to use
    protocols = {
        'StopAndWait': StopAndWaitSender,
        'GoBackN': GoBackNSender
    }

    SenderClass = protocols[protocol]

    # Create a socket connection to the receiver
    server_address = ('localhost', 12345)  # Replace with actual receiver's IP and port
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        connection.connect(server_address)
        print(f"Connected to receiver at {server_address}")

        # Initialize the sender
        sender = SenderClass(
            connection=connection,
            input_file=file_path,
            source=source_address,
            destination=destination_address,
            checker=technique,
            bytes=packet_size,
            window_size=4 if protocol == 'GoBackN' else None  # Example window size for GoBackN
        )

        # Start sending data
        sender.send_data()

    except Exception as e:
        print(f"Failed to connect to the receiver: {e}")
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    main()
