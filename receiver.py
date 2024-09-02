import sys
import socket
from stop_and_wait import Receiver as StopAndWaitReceiver
from go_back_n import Receiver as GoBackNReceiver

def main():
    # Ensure the correct number of command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python receiver.py <protocol> <technique>")
        print("Protocol: 'StopAndWait' or '1', 'GoBackN' or '2'")
        print("Technique: 'CRC' or '1', 'Checksum' or '2'")
        sys.exit(1)

    # Extract command-line arguments
    protocol_input = sys.argv[1]
    technique_input = sys.argv[2]

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

    # Hardcoded MAC address for the receiver (example address)
    receiver_address = b'\x06\x05\x04\x03\x02\x01'

    # Mapping of protocols to receiver classes
    protocols = {
        'StopAndWait': StopAndWaitReceiver,
        'GoBackN': GoBackNReceiver
    }

    ReceiverClass = protocols[protocol]

    # Create a socket to listen for incoming connections
    server_address = ('localhost', 12345)  # Replace with the desired IP and port for the receiver
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        connection.bind(server_address)
        connection.listen(1)
        print(f"Receiver listening on {server_address} using protocol '{protocol}' with technique '{technique}'.")

        while True:
            try:
                client_socket, client_address = connection.accept()
                print(f"Connection established with {client_address}")

                # Initialize the receiver with the provided arguments
                receiver = ReceiverClass(
                    connection=client_socket,
                    checker=technique,
                    address=receiver_address
                )

                # Start receiving data
                receiver.receive_data()

            except Exception as e:
                print(f"Error during connection: {e}")
            finally:
                client_socket.close()
                print(f"Connection closed with {client_address}")

    except Exception as e:
        print(f"Failed to set up the receiver: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    main()
