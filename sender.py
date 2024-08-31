import sys
import socket
from stop_and_wait import Sender as StopAndWaitSender
from go_back_n import Sender as GoBackNSender

def main():
    # Ensure the correct number of command-line arguments
    if len(sys.argv) != 5:
        print("Usage: python sender.py <protocol> <file_path> <packet_size> <technique>")
        sys.exit(1)

    # Extract command-line arguments
    protocol = sys.argv[1]
    file_path = sys.argv[2]
    packet_size = int(sys.argv[3])
    technique = sys.argv[4]

    # Hardcoded MAC addresses (example addresses)
    source_address = b'\x01\x02\x03\x04\x05\x06'
    destination_address = b'\x06\x05\x04\x03\x02\x01'

    # Choose the error checking scheme based on the technique argument
    techniques = ['CRC', 'Checksum']
    if technique not in techniques:
        print("Error: Technique must be either 'CRC' or 'Checksum'.")
        sys.exit(1)

    # Determine the protocol to use
    protocols = {
        'StopAndWait': StopAndWaitSender,
        'GoBackN': GoBackNSender
    }

    if protocol not in protocols:
        print("Error: Protocol must be either 'StopAndWait' or 'GoBackN'.")
        sys.exit(1)

    # Get the appropriate sender class
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
            bytes=packet_size
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
