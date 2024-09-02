import struct
from error_checker import CRC, Checksum

class DataFrame:
    def __init__(self, source_address, destination_address, length, frame_seq_no, payload, error_checking_scheme):
        self.source_address = source_address
        self.destination_address = destination_address
        self.length = length
        self.frame_seq_no = frame_seq_no
        self.payload = payload
        self.error_checking_scheme = error_checking_scheme

        if error_checking_scheme == "CRC":
            crc = CRC()
            self.fcs = crc.generate_fcs(payload)
        elif error_checking_scheme == "Checksum":
            checksum = Checksum()
            self.fcs = checksum.generate_fcs(payload)

    def to_bytes(self):
        header = struct.pack('!6s6sHB', self.source_address,
                             self.destination_address, self.length, self.frame_seq_no)
        payload_bytes = self.payload.encode('utf-8')
        fcs_bytes = bytes(int(self.fcs[i:i+8], 2)
                          for i in range(0, len(self.fcs), 8))
        return header + payload_bytes + fcs_bytes

    @staticmethod
    def from_bytes(data):
        source_address = data[:6]  # Extract 6 bytes for source address
        # Extract 6 bytes for destination address
        destination_address = data[6:12]
        length = struct.unpack('!H', data[12:14])[
            0]  # Extract 2 bytes for length
        # Extract 1 byte for frame sequence number
        frame_seq_no = struct.unpack('B', data[14:15])[0]

        # Correct payload extraction
        payload = data[15:-4].decode('utf-8')

        # Correct FCS extraction as binary
        fcs = ''.join(format(byte, '08b') for byte in data[-4:])

        dataframe = DataFrame(
            source_address, destination_address, length, frame_seq_no, payload, None)
        dataframe.fcs = fcs
        return dataframe


# Example to test the new DataFrame class
if __name__ == "__main__":
    # Sample Data
    src = b'\x01\x02\x03\x04\x05\x06'
    dst = b'\xaa\xbb\xcc\xdd\xee\xff'
    length = 64
    seq_no = 1
    payload = "11010110101101011010101101101010111111111"
    scheme = "CRC"

    # Create DataFrame instance
    df = DataFrame(src, dst, length, seq_no, payload, scheme)

    # Serialize to bytes
    serialized_df = df.to_bytes()

    # Deserialize from bytes
    received_df = DataFrame.from_bytes(serialized_df)

    # Output Results
    print(f"Original Payload: {df.payload}")
    print(f"Received Payload: {received_df.payload}")
    print(f"Original FCS: {df.fcs}")
    print(f"Received FCS: {received_df.fcs}")