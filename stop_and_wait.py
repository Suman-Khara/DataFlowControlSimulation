import threading
import time
import socket
from channel import Channel
from dataframe import DataFrame
from ackframe import ACK  # Assuming ACK is a class that has a from_bytes method
from error_checker import CRC, Checksum


class Sender:
    def __init__(self, connection, input_file, source, destination, checker, bytes, log_file="log.txt"):
        self.connection = connection
        self.input_file = input_file
        self.source_address = source
        self.destination_address = destination
        self.error_checker = checker
        self.channel = Channel()
        self.index = 0
        self.payload_size = bytes
        self.log_file = log_file
        self.lock = threading.Lock()
        self.ack_received = False
        self.stop_sending = False  # Flag to indicate the end of transmission

    def makeDataFrame(self):
        # Calculate the starting character index and the number of characters to read
        start_char_index = self.index * self.payload_size * 8
        num_chars_to_read = self.payload_size * 8

        with open(self.input_file, 'r') as input:  # Open the file in text mode
            # Move to the starting character index
            input.seek(start_char_index)
            # Read the specified number of characters
            data = input.read(num_chars_to_read)

            if not data:
                return None  # End of file reached

        dataframe = DataFrame(self.source_address, self.destination_address, self.payload_size, self.index, data, self.error_checker)
        return dataframe

    def send_data(self):
        with open(self.log_file, 'w'):
            pass

        while not self.stop_sending:
            # Create a data frame
            dataframe = self.makeDataFrame()

            # Check if end of file is reached
            if dataframe is None:
                print("End of file reached. Terminating connection.")
                self.stop_sending = True  # Set flag to stop sending
                break

            # Infinite loop for sending the same frame until ACK is received
            first_attempt = True
            while not self.stop_sending:
                # Pass the data frame through the channel
                transmitted_df = self.channel.transmit(dataframe)

                if transmitted_df is None:
                    # Frame was lost
                    time.sleep(2)
                    if first_attempt:
                        self.log(f"{self.index} sent")
                        first_attempt = False
                    else:
                        self.log(f"{self.index} re-sent")
                    print(f"Frame {self.index} lost during transmission. Re-sending after timeout.")
                else:
                    # Convert the transmitted dataframe to bytes and send through the connection
                    data_to_send = transmitted_df.to_bytes()
                    self.connection.sendall(data_to_send)

                    # Log as "sent" or "re-sent" depending on the attempt
                    if first_attempt:
                        self.log(f"{self.index} sent")
                        first_attempt = False
                    else:
                        self.log(f"{self.index} re-sent")

                    print(f"Frame {self.index} sent. Waiting for ACK...")

                    # Start a thread to wait for an ACK
                    ack_thread = threading.Thread(target=self.wait_for_ack)
                    ack_thread.start()

                    # Wait for the ACK thread to complete or timeout
                    ack_thread.join(timeout=2)

                    # If ACK is received, break the loop to proceed to the next frame
                    if self.ack_received:
                        print(f"ACK received for Frame {self.index}. Proceeding to next frame.")
                        self.ack_received = False
                        self.index += 1
                        break
                    else:
                        print(f"Timeout waiting for ACK for Frame {self.index}. Re-sending...")

        # Ensure all threads finish before closing the connection
        print("Closing connection after all frames are sent.")
        self.connection.close()

    def wait_for_ack(self):
        try:
            # Wait for ACK frame
            ack_data = self.connection.recv(1024)  # Buffer size is 1024 bytes
            if ack_data:
                self.ack_received = True
        except socket.timeout:
            print(f"Timeout waiting for ACK for Frame {self.index}")
        except ConnectionAbortedError:
            print("Connection was closed while waiting for ACK.")
        except OSError as e:
            print(f"Error receiving ACK: {e}")

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
        self.index = 1  # Start indexing from 1
        self.address = address

    def receive_data(self):
        # Open output file in write mode
        with open(self.output_file, 'w') as output:
            while True:
                try:
                    # Receive data frame
                    # Buffer size is 1024 bytes
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
                    # Calculate payload size in bits
                    self.payload_size = len(payload) * 8

                    # Validate data using the error checker
                    if self.error_checker.validate(payload, received_fcs):
                        print(f"{self.index}. accepted")

                        # Create and send ACK frame
                        ack_frame = ACK(
                            source_address=self.address,
                            destination_address=data_frame.source_address,
                            frame_seq_no=0
                        )
                        self.connection.sendall(ack_frame.to_bytes())

                        # Write accepted payload to output file
                        output.write(f"{self.index}. {payload}\n")
                        self.index += 1

                    else:
                        print(f"{self.index}. rejected")

                except Exception as e:
                    print(f"Error receiving data: {e}")
                    self.connection.close()
                    break

        # Validate received data against the original input file after the connection is closed
        self.validate_output()

    def validate_output(self):
        print("Validation begins...")
        with open(self.input_file, 'r') as input_file, open(self.output_file, 'r+') as output_file:
            # Read all bits from input file as a continuous string
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
