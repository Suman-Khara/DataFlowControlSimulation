WINDOW_SIZE=3

import threading
import socket
from collections import deque
from channel import Channel
from dataframe import DataFrame
from ackframe import ACK  # Assuming ACK is a class that has a from_bytes method
from error_checker import CRC, Checksum


class Sender:
    def __init__(self, connection, input_file, source, destination, checker, bytes, log_file="log.txt", window_size=WINDOW_SIZE):
        self.connection = connection
        self.input_file = input_file
        self.source_address = source
        self.destination_address = destination
        self.error_checker = checker
        self.payload_size = bytes
        self.log_file = log_file
        self.channel = Channel()
        self.index = 0
        self.window_size = window_size
        self.dataframe_queue = deque()  # Queue for data frames to be sent
        self.ack_buffer = deque()  # Queue for ACK frames received
        self.lock = threading.Lock()
        self.stop_sending = False

    def makeDataFrame(self):
        # Calculate the starting character index and the number of characters to read
        start_char_index = self.index * self.payload_size * 8
        num_chars_to_read = self.payload_size * 8

        with open(self.input_file, 'r') as input:
            input.seek(start_char_index)
            data = input.read(num_chars_to_read)

            if not data:
                return None  # End of file reached

        dataframe = DataFrame(self.source_address, self.destination_address, self.payload_size, self.index, data, self.error_checker)
        return dataframe

    def send_data(self):
        with open(self.log_file, 'w'):
            pass

        # Main sending loop
        while not self.stop_sending:
            # Check if the window size is not full
            if len(self.dataframe_queue) < self.window_size:
                dataframe = self.makeDataFrame()

                if dataframe is None:
                    print("End of file reached. Terminating connection.")
                    self.stop_sending = True  # No more frames to send
                    break

                # Pass the data frame through the channel
                transmitted_df = self.channel.transmit(dataframe)

                if transmitted_df is not None:
                    self.dataframe_queue.append(transmitted_df)
                    data_to_send = transmitted_df.to_bytes()
                    self.connection.sendall(data_to_send)
                    self.log(f"{self.index} sent")
                    print(f"Frame {self.index} sent.")
                    self.index += 1

            # Receive ACKs and manage the data frame queue
            self.receive_ack()

            # Check if ACKs received for all frames in the queue
            while self.dataframe_queue:
                ack_thread = threading.Thread(target=self.wait_for_ack)
                ack_thread.start()
                ack_thread.join(timeout=2)

                # If no ACKs were received, retransmit all frames in the queue
                if not self.ack_buffer:
                    print("Timeout. Retransmitting all frames in the window.")
                    self.retransmit_frames()

        # Ensure all threads finish before closing the connection
        print("Closing connection after all frames are sent.")
        self.connection.close()

    def receive_ack(self):
        try:
            # Receive ACK frame
            ack_data = self.connection.recv(1024)  # Buffer size is 1024 bytes

            if ack_data:
                ack_frame = ACK.from_bytes(ack_data)
                self.ack_buffer.append(ack_frame)

                # Process ACKs and update the frame queue
                while self.ack_buffer:
                    ack_frame = self.ack_buffer.popleft()
                    if self.dataframe_queue and ack_frame.frame_seq_no >= self.dataframe_queue[0].frame_seq_no:
                        self.log(f"ACK {ack_frame.frame_seq_no} received.")
                        self.dataframe_queue.popleft()

        except socket.timeout:
            print("Timeout waiting for ACK.")
        except ConnectionAbortedError:
            print("Connection was closed while waiting for ACK.")
        except OSError as e:
            print(f"Error receiving ACK: {e}")

    def wait_for_ack(self):
        try:
            ack_data = self.connection.recv(1024)
            if ack_data:
                ack_frame = ACK.from_bytes(ack_data)
                self.ack_buffer.append(ack_frame)
        except socket.timeout:
            print("Timeout waiting for ACK.")
        except ConnectionAbortedError:
            print("Connection was closed while waiting for ACK.")
        except OSError as e:
            print(f"Error receiving ACK: {e}")

    def retransmit_frames(self):
        for frame in self.dataframe_queue:
            transmitted_df = self.channel.transmit(frame)
            if transmitted_df is not None:
                data_to_send = transmitted_df.to_bytes()
                self.connection.sendall(data_to_send)
                self.log(f"{frame.frame_seq_no} re-sent")
                print(f"Frame {frame.frame_seq_no} re-sent.")

    def log(self, message):
        with self.lock:
            with open(self.log_file, 'a') as log:
                log.write(f"{message}\n")


class Receiver:
    def __init__(self, connection, checker, address, input_file='input.txt', output_file="output.txt"):
        self.connection = connection
        self.input_file = input_file
        self.output_file = output_file
        if checker == 'CRC':
            self.error_checker = CRC()
        elif checker == 'Checksum':
            self.error_checker = Checksum()
        self.expected_seq_num = 0  # Sequence number expected by the receiver
        self.address = address

    def receive_data(self):
        """Main function to receive data using the Go-Back-N protocol."""
        with open(self.output_file, 'w') as output:
            while True:
                try:
                    # Receive data frame
                    data = self.connection.recv(1024)
                    
                    if not data:
                        print("Connection closed by client.")
                        self.connection.close()
                        break

                    # Convert bytes to data frame object
                    data_frame = DataFrame.from_bytes(data)

                    # Check if the destination address matches the server address
                    if data_frame.destination_address != self.address:
                        print("Destination address mismatch. Closing connection.")
                        self.connection.close()
                        break

                    # Extract payload and FCS
                    payload = data_frame.payload
                    received_fcs = data_frame.fcs
                    self.payload_size = len(payload) * 8

                    # Validate data using the error checker
                    if self.error_checker.validate(payload, received_fcs):
                        if data_frame.frame_seq_no == self.expected_seq_num:
                            print(f"Frame {self.expected_seq_num} accepted.")

                            # Write accepted payload to output file with index
                            output.write(f"{self.expected_seq_num}. {payload}\n")

                            # Increment the expected sequence number
                            self.expected_seq_num += 1
                        else:
                            print(f"Frame {data_frame.frame_seq_no} out of order. Expected {self.expected_seq_num}. Ignoring.")

                        # Always send an ACK for the last correctly received frame
                        ack_frame = ACK(
                            source_address=self.address,
                            destination_address=data_frame.source_address,
                            frame_seq_no=self.expected_seq_num - 1
                        )
                        self.connection.sendall(ack_frame.to_bytes())
                        print(f"ACK for Frame {self.expected_seq_num - 1} sent.")
                    else:
                        print(f"Frame {data_frame.frame_seq_no} rejected due to error.")
                        # If the frame is rejected, resend ACK for the last correctly received frame
                        ack_frame = ACK(
                            source_address=self.address,
                            destination_address=data_frame.source_address,
                            frame_seq_no=self.expected_seq_num - 1
                        )
                        self.connection.sendall(ack_frame.to_bytes())
                        print(f"ACK for Frame {self.expected_seq_num - 1} re-sent due to error.")

                except Exception as e:
                    print(f"Error receiving data: {e}")
                    self.connection.close()
                    break

        # Validate received data against the original input file after the connection is closed
        self.validate_output()

    def validate_output(self):
        """Validates the received data against the original input file."""
        print("Validation begins...")
        with open(self.input_file, 'r') as input_file, open(self.output_file, 'r+') as output_file:
            input_data = input_file.read().strip()
            output_lines = output_file.readlines()

            # Go to the beginning of the output file to rewrite any incorrect frames
            output_file.seek(0)

            for index, line in enumerate(output_lines):
                start = index * self.payload_size // 8
                end = (index + 1) * self.payload_size // 8
                if end > len(input_data):
                    break

                # Extract payload from the input file, assuming each payload size
                expected_payload = input_data[start:end]

                # Extract payload from the output file
                line_payload = line.strip().split('. ')[1]

                # Check if the output matches the input payload
                if line_payload != expected_payload:
                    # Append "(incorrect)" if the payload does not match
                    output_file.write(f"{line.strip()} (incorrect)\n")
                else:
                    output_file.write(line)

            # Truncate the rest of the file
            output_file.truncate()

        print("Validation complete.")
