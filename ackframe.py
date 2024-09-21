import struct

class ACK:
    def __init__(self, source_address, destination_address, frame_seq_no):
        self.source_address = source_address
        self.destination_address = destination_address
        self.frame_seq_no = frame_seq_no

    def to_bytes(self):
        # Ensure that frame_seq_no is a signed 8-bit integer (-128 to 127). negative frame sequence number means NAK
        if not isinstance(self.frame_seq_no, int) or not (-128 <= self.frame_seq_no <= 127):
            raise ValueError("Frame sequence number must be an integer between -128 and 127.")
        
        # Pack the addresses as 6-byte strings and frame_seq_no as a signed byte
        header = struct.pack('!6s6sb', self.source_address, self.destination_address, self.frame_seq_no)
        return header
    
    @staticmethod
    def from_bytes(data):
        # Unpack source_address (first 6 bytes), destination_address (next 6 bytes), and signed frame_seq_no (last byte)
        source_address = data[:6]
        destination_address = data[6:12]
        frame_seq_no = struct.unpack('b', data[12:13])[0]  # Unpack as signed byte
        return ACK(source_address, destination_address, frame_seq_no)