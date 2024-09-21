import sys
import socket
from stop_and_wait import Sender as StopAndWaitSender
from go_back_n import Sender as GoBackNSender
from selective_repeat import Sender as SelectiveRepeatSender

def main():
    if len(sys.argv) != 5:
        print("Usage: python sender.py <protocol> <file_path> <packet_size> <technique>")
        print("Protocol: 'StopAndWait' or '1', 'GoBackN' or '2', or 'SelectiveRepeat' or '3'")
        print("Technique: 'CRC' or '1', 'Checksum' or '2'")
        sys.exit(1)

    protocol_input = sys.argv[1]
    file_path = sys.argv[2]
    packet_size = int(sys.argv[3])
    technique_input = sys.argv[4]

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

    source_address = b'\x01\x02\x03\x04\x05\x06'
    destination_address = b'\x06\x05\x04\x03\x02\x01'

    protocols = {
        'StopAndWait': StopAndWaitSender,
        'GoBackN': GoBackNSender,
        'SelectiveRepeat': SelectiveRepeatSender
    }

    SenderClass = protocols[protocol]

    server_address = ('localhost', 12345)
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    connection.connect(server_address)
    print(f"Connected to receiver at {server_address}")

    sender = SenderClass(
        connection=connection,
        input_file=file_path,
        source=source_address,
        destination=destination_address,
        checker=technique,
        bytes=packet_size
    )

    sender.send_data()

    connection.close()

if __name__ == "__main__":
    main()
