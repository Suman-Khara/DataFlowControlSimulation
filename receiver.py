import sys
import socket
from stop_and_wait import Receiver as StopAndWaitReceiver
from go_back_n import Receiver as GoBackNReceiver

def main():
    # Ensure the correct number of command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python receiver.py <protocol> <technique>")
        sys.exit(1)

    # Extract command-line arguments
    protocol = sys.argv[1]
    technique = sys.argv[2]

    # Hardcoded MAC address for the receiver (example address)
    receiver_address = b'\x06\x05\x04\x03\x02\x01'

    # Mapping of protocols to receiver classes
    protocols = {
        'StopAndWait': StopAndWaitReceiver,
        'GoBackN': GoBackNReceiver
    }

    # Validate protocol and technique
    if protocol not in protocols:
        print("Error: Protocol must be either 'StopAndWait' or 'GoBackN'.")
        sys.exit(1)

    # Get the appropriate receiver class and error checker
    ReceiverClass = protocols[protocol]

    # Choose the error checking scheme based on the technique argument
    techniques = ['CRC', 'Checksum']
    if technique not in techniques:
        print("Error: Technique must be either 'CRC' or 'Checksum'.")
        sys.exit(1)
    
    # Create a socket to listen for incoming connections
    server_address = ('localhost', 12345)  # Replace with the desired IP and port for the receiver
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.bind(server_address)
    connection.listen(1)

    print(f"Receiver listening on {server_address}")

    while True:
        try:
            client_socket, client_address = connection.accept()
            print(f"Connection established with {client_address}")

            # Initialize the receiver with the provided arguments
            receiver = ReceiverClass(
                connection=client_socket,
                input_file='input.txt',
                output_file='output.txt',
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

if __name__ == "__main__":
    main()