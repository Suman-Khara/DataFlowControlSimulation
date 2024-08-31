import struct


class ACK:
    def __init__(self, source_address, destination_address, frame_seq_no):
        self.source_address = source_address
        self.destination_address = destination_address
        self.frame_seq_no = frame_seq_no

    def to_bytes(self):
        # Serialize the ACK frame to bytes
        header = struct.pack('!6s6sB', self.source_address, self.destination_address, self.frame_seq_no)
        return header

    @staticmethod
    def from_bytes(data):
        # Deserialize the ACK frame from bytes
        source_address = data[:6]  # Extract 6 bytes for source address
        destination_address = data[6:12]  # Extract 6 bytes for destination address
        frame_seq_no = struct.unpack('B', data[12:13])[0]  # Extract 1 byte for frame sequence number
        return ACK(source_address, destination_address, frame_seq_no)


class NACK:
    def __init__(self, source_address, destination_address, frame_seq_no):
        self.source_address = source_address
        self.destination_address = destination_address
        self.frame_seq_no = frame_seq_no

    def to_bytes(self):
        # Serialize the NACK frame to bytes
        header = struct.pack('!6s6sB', self.source_address, self.destination_address, self.frame_seq_no)
        return header

    @staticmethod
    def from_bytes(data):
        # Deserialize the NACK frame from bytes
        source_address = data[:6]  # Extract 6 bytes for source address
        destination_address = data[6:12]  # Extract 6 bytes for destination address
        frame_seq_no = struct.unpack('B', data[12:13])[0]  # Extract 1 byte for frame sequence number
        return NACK(source_address, destination_address, frame_seq_no)


# Example to test the ACK and NACK classes
if __name__ == "__main__":
    # Sample Data
    src = b'\x01\x02\x03\x04\x05\x06'
    dst = b'\xaa\xbb\xcc\xdd\xee\xff'
    seq_no = 1

    # Create ACK instance
    ack_frame = ACK(src, dst, seq_no)

    # Serialize ACK to bytes
    serialized_ack = ack_frame.to_bytes()

    # Deserialize ACK from bytes
    received_ack = ACK.from_bytes(serialized_ack)

    # Output Results for ACK
    print(f"ACK Original Frame Seq No: {ack_frame.frame_seq_no}")
    print(f"ACK Received Frame Seq No: {received_ack.frame_seq_no}")

    # Create NACK instance
    nack_frame = NACK(src, dst, seq_no)

    # Serialize NACK to bytes
    serialized_nack = nack_frame.to_bytes()

    # Deserialize NACK from bytes
    received_nack = NACK.from_bytes(serialized_nack)

    # Output Results for NACK
    print(f"NACK Original Frame Seq No: {nack_frame.frame_seq_no}")
    print(f"NACK Received Frame Seq No: {received_nack.frame_seq_no}")
