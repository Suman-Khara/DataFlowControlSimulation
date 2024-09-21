import sys
import socket
from stop_and_wait import Receiver as StopAndWaitReceiver
from go_back_n import Receiver as GoBackNReceiver
from selective_repeat import Receiver as SelectiveRepeatReceiver

def main():
    if len(sys.argv) != 3:
        print("Usage: python receiver.py <protocol> <technique>")
        print("Protocol: 'StopAndWait' or '1', 'GoBackN' or '2', or 'SelectiveRepeat' or '3'")
        print("Technique: 'CRC' or '1', 'Checksum' or '2'")
        sys.exit(1)

    protocol_input = sys.argv[1]
    technique_input = sys.argv[2]

    protocol_map = {
        '1': 'StopAndWait',
        '2': 'GoBackN',
        '3': 'SelectiveRepeat',
        'StopAndWait': 'StopAndWait',
        'GoBackN': 'GoBackN',
        'SelectiveRepeat': 'SelectiveRepeat'
    }

    technique_map = {
        '1': 'CRC',
        '2': 'Checksum',
        'CRC': 'CRC',
        'Checksum': 'Checksum'
    }

    protocol = protocol_map.get(protocol_input)
    if not protocol:
        print("Error: Invalid protocol. Choose 'StopAndWait', 'GoBackN', 'SelectiveRepeat', '1', '2', or '3'.")
        sys.exit(1)

    technique = technique_map.get(technique_input)
    if not technique:
        print("Error: Technique must be either 'CRC', 'Checksum', '1', or '2'.")
        sys.exit(1)

    receiver_address = b'\x06\x05\x04\x03\x02\x01'

    protocols = {
        'StopAndWait': StopAndWaitReceiver,
        'GoBackN': GoBackNReceiver,
        'SelectiveRepeat': SelectiveRepeatReceiver
    }

    ReceiverClass = protocols[protocol]

    server_address = ('localhost', 12345)
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    connection.bind(server_address)
    connection.listen(1)
    print(f"Receiver listening on {server_address} using protocol '{protocol}' with technique '{technique}'.")

    while True:
        client_socket, client_address = connection.accept()
        print(f"Connection established with {client_address}")

        receiver = ReceiverClass(
            connection=client_socket,
            checker=technique,
            address=receiver_address
        )

        receiver.receive_data()

        client_socket.close()
        print(f"Connection closed with {client_address}")

    connection.close()

if __name__ == "__main__":
    main()
