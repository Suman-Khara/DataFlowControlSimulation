import traceback
import threading
import time
from channel import Channel
from dataframe import DataFrame
from ackframe import ACK
from error_checker import CRC, Checksum

WINDOW_SIZE=4
TIMEOUT=4

class Sender:
    def __init__(self, connection, input_file, source, destination, checker, bytes, log_file="log.txt", window_size=WINDOW_SIZE, timeout=TIMEOUT):
        self.connection = connection
        self.input_file = input_file
        self.source_address = source
        self.destination_address = destination
        self.error_checker = checker
        self.payload_size = bytes
        self.log_file = log_file
        self.window_size = window_size
        self.timeout = timeout
        self.channel = Channel()
        self.buffer = {}  # Stores frame sequence number as key, and (thread, dataframe) as value
        self.lock = threading.Lock()  # For synchronizing access to the buffer
        self.ack_received = threading.Event()  # Event signaling the receipt of ACK/NACK

    def makeDataFrame(self, index):
        start_char_index = index * self.payload_size * 8
        num_chars_to_read = self.payload_size * 8

        with open(self.input_file, 'r') as input_file:
            input_file.seek(start_char_index)
            data = input_file.read(num_chars_to_read)

            if not data:
                return None

        dataframe = DataFrame(self.source_address, self.destination_address, self.payload_size, index, data, self.error_checker)
        return dataframe

    def send_data(self):
        with open(self.log_file, 'w'):
            pass
        frame_seq_no = 0

        # Start the listener thread for ACKs and NACKs
        listener_thread = threading.Thread(target=self.listen_for_acks)
        listener_thread.start()

        while True:
            # Fill the buffer until the window size is reached or end of file
            while len(self.buffer) < self.window_size:
                dataframe = self.makeDataFrame(frame_seq_no)
                if dataframe is None:
                    break  # End of file reached

                # Create and store a new thread for the frame
                frame_thread = threading.Thread(target=self.send_frame, args=(dataframe,))
                self.buffer[frame_seq_no] = (frame_thread, dataframe)
                frame_thread.start()
                frame_seq_no += 1

            # Wait for the ACK/NACK processing
            self.ack_received.wait()

            # ACKs/NACKs are handled by another thread (ACK listener)
            self.ack_received.clear()

            # If buffer is empty and no more frames to send, transmission is done
            if len(self.buffer) == 0 and dataframe is None:
                print("Transmission completed.")
                break

        # Wait for the listener thread to finish before exiting
        listener_thread.join()

    def send_frame(self, dataframe):
        frame_seq_no = dataframe.frame_seq_no
        while True:
            # Pass the frame through the channel (introducing possible errors/loss)
            transmitted_frame = self.channel.transmit(dataframe)
            with open(self.log_file, 'a') as log_file:
                if dataframe.first_time:
                    log_file.write(f"{dataframe.frame_seq_no}. Sent\n")
                else:
                    log_file.write(f"{dataframe.frame_seq_no}. Resent\n")
            dataframe.first_time=False
            if transmitted_frame is not None:
                # Send the frame over the connection
                self.connection.send(transmitted_frame.to_bytes())
                print(f"Sent frame: {frame_seq_no}")

            # Start timer for timeout
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                # Wait for an ACK or NACK
                with self.lock:
                    if frame_seq_no not in self.buffer:
                        return  # Frame successfully acknowledged, stop retransmission

            # Timeout occurred, retransmit the frame
            print(f"Timeout, retransmitting frame: {frame_seq_no}")

    def handle_ack(self, ack_frame):
        with self.lock:
            ack_seq_no = ack_frame.frame_seq_no
            # Remove all frames with sequence numbers <= ACKed frame from buffer
            for seq_no in list(self.buffer.keys()):
                if seq_no <= ack_seq_no:
                    frame_thread, dataframe = self.buffer.pop(seq_no)
                    print(f"ACK received for frame: {seq_no}, removing from buffer.")
                    # Terminate the thread (it should finish on its own after this)

            # Signal that ACK has been processed
            self.ack_received.set()

    def handle_nack(self, nack_frame):
        with self.lock:
            nack_seq_no = -nack_frame.frame_seq_no-1
            # Resend the specific frame indicated by the NACK
            if nack_seq_no in self.buffer:
                frame_thread, dataframe = self.buffer[nack_seq_no]
                print(f"NACK received for frame: {nack_seq_no}, resending.")
                # The thread will automatically retransmit on its next cycle (timeout)
                # Optionally restart the thread or set a flag to trigger immediate retransmission
                frame_thread = threading.Thread(target=self.send_frame, args=(dataframe,))
                self.buffer[nack_seq_no] = (frame_thread, dataframe)
                frame_thread.start()

    def listen_for_acks(self):
        """Listen for ACK and NAK frames continuously."""
        while True:
            ack_nack_data = self.connection.recv(1024)  # Assuming a fixed size for ACK/NACK frames
            ack_nack_frame = ACK.from_bytes(ack_nack_data)  # Deserialize frame

            if ack_nack_frame.frame_seq_no >= 0:
                self.handle_ack(ack_nack_frame)
            else:
                self.handle_nack(ack_nack_frame)

class Receiver:
    def __init__(self, connection, checker, address, window_size=WINDOW_SIZE, input_file='input.txt', output_file="output.txt"):
        self.connection = connection
        self.input_file = input_file
        self.output_file = output_file
        self.window_size = window_size
        self.expected_seq_no = 0  # First sequence number expected
        self.address = address
        self.buffer = [None] * window_size  # Buffer of window size to hold out-of-order frames

        # Initialize error checker (CRC or Checksum)
        if checker == 'CRC':
            self.error_checker = CRC()
        elif checker == 'Checksum':
            self.error_checker = Checksum()

    def receive_data(self):
        with open(self.output_file, 'w') as output:
            while True:
                try:
                    # Receive data from sender
                    data = self.connection.recv(1024)
                    if not data:
                        print("Connection closed by sender.")
                        self.connection.close()
                        break

                    # Convert received data to DataFrame object
                    data_frame = DataFrame.from_bytes(data)

                    # Address verification
                    if data_frame.destination_address != self.address:
                        print("Destination address mismatch. Closing connection.")
                        self.connection.close()
                        break

                    frame_seq_no = data_frame.frame_seq_no
                    payload = data_frame.payload
                    received_fcs = data_frame.fcs
                    self.payload_size = len(payload) * 8  # Size of the payload in bits

                    # Case 1: Frame with expected sequence number
                    if frame_seq_no == self.expected_seq_no:
                        print(f"Frame {frame_seq_no} received (in order).")
                        if self.error_checker.validate(payload, received_fcs):  # No errors
                            #output.write(f"{frame_seq_no}. {payload}\n")
                            self.send_ack(frame_seq_no)
                            self.buffer[0] = data_frame  # Store in buffer

                            # Check and flush buffer for consecutive frames
                            self.flush_buffer(output)

                        else:  # Frame has errors
                            print(f"Frame {frame_seq_no} rejected (FCS error).")
                            self.send_nack(frame_seq_no)

                    # Case 2: Frame with sequence number greater than expected
                    elif frame_seq_no > self.expected_seq_no:
                        print(f"Frame {frame_seq_no} received (out of order).")

                        # Send NACKs for missing frames up to current frame
                        for seq in range(self.expected_seq_no, frame_seq_no):
                            self.send_nack(seq)

                        # Check if frame is already in buffer
                        buffer_index = (frame_seq_no - self.expected_seq_no) % self.window_size
                        if self.buffer[buffer_index] is None:
                            if self.error_checker.validate(payload, received_fcs):  # No errors
                                print(f"Frame {frame_seq_no} stored in buffer.")
                                self.buffer[buffer_index] = data_frame
                            else:  # Frame has errors
                                print(f"Frame {frame_seq_no} rejected (FCS error).")
                                self.send_nack(frame_seq_no)

                    # Case 3: Frame with sequence number less than expected
                    else:
                        print(f"Duplicate frame {frame_seq_no} received.")
                        # ACK for previous frame since this frame has already been acknowledged
                        self.send_ack(self.expected_seq_no - 1)

                except Exception as e:
                    print(f"Error receiving data: {e}")
                    traceback.print_exc()
                    self.connection.close()
                    break

        # After connection closes, validate the output
        self.validate_output()

    def flush_buffer(self, output):
        """Writes the in-sequence frames from the buffer to the output file."""
        while self.buffer[0] is not None:  # Start from the beginning of the buffer
            frame = self.buffer.pop(0)  # Remove the first frame in the buffer
            self.buffer.append(None)  # Append an empty slot at the end
            payload = frame.payload
            output.write(f"{self.expected_seq_no}. {payload}\n")
            print(f"Flushed frame {self.expected_seq_no} to output.")
            self.expected_seq_no += 1  # Increment expected sequence number

    def send_ack(self, seq_no):
        """Sends an ACK for the given sequence number."""
        ack_frame = ACK(source_address=self.address, destination_address=self.address, frame_seq_no=seq_no)
        self.connection.sendall(ack_frame.to_bytes())
        print(f"ACK for frame {seq_no} sent.")

    def send_nack(self, seq_no):
        """Sends a NACK for the given sequence number."""
        nack_frame = ACK(source_address=self.address, destination_address=self.address, frame_seq_no=-seq_no-1)
        self.connection.sendall(nack_frame.to_bytes())
        print(f"NACK for frame {seq_no} sent.")

    def validate_output(self):
        """Validates the received data against the original input file."""
        print("Validation begins...")
        with open(self.input_file, 'r') as input_file, open(self.output_file, 'r+') as output_file:
            input_data = input_file.read().strip()
            output_lines = output_file.readlines()

            output_file.seek(0)

            for index, line in enumerate(output_lines):
                start = index * self.payload_size // 8
                end = (index + 1) * self.payload_size // 8
                if end > len(input_data):
                    break

                expected_payload = input_data[start:end]
                line_payload = line.strip().split('. ')[1]

                if line_payload != expected_payload:
                    output_file.write(f"{line.strip()} (incorrect)\n")
                else:
                    output_file.write(line)

            output_file.truncate()

        print("Validation complete.")
