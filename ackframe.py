import struct

class ACK:
    def __init__(self, source_address, destination_address, frame_seq_no):
        self.source_address = source_address
        self.destination_address = destination_address
        self.frame_seq_no = frame_seq_no

    def to_bytes(self):
        if not isinstance(self.frame_seq_no, int) or not (0 <= self.frame_seq_no <= 255):
            raise ValueError("Frame sequence number must be an integer between 0 and 255.")
        header = struct.pack('!6s6sB', self.source_address, self.destination_address, self.frame_seq_no)
        return header
    
    @staticmethod
    def from_bytes(data):
        source_address = data[:6]
        destination_address = data[6:12]
        frame_seq_no = struct.unpack('B', data[12:13])[0]
        return ACK(source_address, destination_address, frame_seq_no)

class NACK:
    def __init__(self, source_address, destination_address, frame_seq_no):
        self.source_address = source_address
        self.destination_address = destination_address
        self.frame_seq_no = frame_seq_no

    def to_bytes(self):
        header = struct.pack('!6s6sB', self.source_address, self.destination_address, self.frame_seq_no)
        return header

    @staticmethod
    def from_bytes(data):
        source_address = data[:6]
        destination_address = data[6:12]
        frame_seq_no = struct.unpack('B', data[12:13])[0]
        return NACK(source_address, destination_address, frame_seq_no)

if __name__ == "__main__":
    src = b'\x01\x02\x03\x04\x05\x06'
    dst = b'\xaa\xbb\xcc\xdd\xee\xff'
    seq_no = 1

    ack_frame = ACK(src, dst, seq_no)
    serialized_ack = ack_frame.to_bytes()
    received_ack = ACK.from_bytes(serialized_ack)

    print(f"ACK Original Frame Seq No: {ack_frame.frame_seq_no}")
    print(f"ACK Received Frame Seq No: {received_ack.frame_seq_no}")

    nack_frame = NACK(src, dst, seq_no)
    serialized_nack = nack_frame.to_bytes()
    received_nack = NACK.from_bytes(serialized_nack)

    print(f"NACK Original Frame Seq No: {nack_frame.frame_seq_no}")
    print(f"NACK Received Frame Seq No: {received_nack.frame_seq_no}")
