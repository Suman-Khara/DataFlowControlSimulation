import threading
import time
import socket
from channel import Channel
from dataframe import DataFrame
from ackframe import ACK
from error_checker import CRC, Checksum

TIMEOUT=4

class Sender:
    def __init__(self, connection, input_file, source, destination, checker, bytes, log_file="log.txt", timeout=TIMEOUT):
        self.connection = connection
        self.input_file = input_file
        self.source_address = source
        self.destination_address = destination
        self.error_checker = checker
        self.channel = Channel()
        self.index = 0
        self.payload_size = bytes
        self.log_file = log_file
        self.timeout=timeout
        self.lock = threading.Lock()
        self.ack_received = False
        self.stop_sending = False

    def makeDataFrame(self):
        start_char_index = self.index * self.payload_size * 8
        num_chars_to_read = self.payload_size * 8

        with open(self.input_file, 'r') as input:
            input.seek(start_char_index)
            data = input.read(num_chars_to_read)

            if not data:
                return None

        dataframe = DataFrame(self.source_address, self.destination_address, self.payload_size, self.index, data, self.error_checker)
        return dataframe

    def send_data(self):
        with open(self.log_file, 'w'):
            pass
        start_time=time.time()
        while not self.stop_sending:
            dataframe = self.makeDataFrame()

            if dataframe is None:
                print("End of file reached. Terminating connection.")
                self.stop_sending = True
                break

            first_attempt = True
            while not self.stop_sending:
                transmitted_df = self.channel.transmit(dataframe)

                if transmitted_df is None:
                    time.sleep(2)
                    if first_attempt:
                        self.log(f"{self.index} sent")
                        first_attempt = False
                    else:
                        self.log(f"{self.index} re-sent")
                    print(f"Frame {self.index} lost during transmission. Re-sending after timeout.")
                else:
                    data_to_send = transmitted_df.to_bytes()
                    self.connection.sendall(data_to_send)

                    if first_attempt:
                        self.log(f"{self.index} sent")
                        first_attempt = False
                    else:
                        self.log(f"{self.index} re-sent")

                    print(f"Frame {self.index} sent. Waiting for ACK...")

                    ack_thread = threading.Thread(target=self.wait_for_ack)
                    ack_thread.start()

                    ack_thread.join(timeout=self.timeout)

                    if self.ack_received:
                        print(f"ACK received for Frame {self.index}. Proceeding to next frame.")
                        self.ack_received = False
                        self.index += 1
                        break
                    else:
                        print(f"Timeout waiting for ACK for Frame {self.index}. Re-sending...")
        end_time=time.time()
        total_time = end_time - start_time
        print(f"Total transmission time: {total_time:.2f} seconds")
        print("Closing connection after all frames are sent.")
        self.connection.close()

    def wait_for_ack(self):
        try:
            ack_data = self.connection.recv(1024)
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
        self.index = 0
        self.address = address

    def receive_data(self):
        with open(self.output_file, 'w') as output:
            while True:
                try:
                    data = self.connection.recv(1024)

                    if not data:
                        print("Connection closed by client.")
                        self.connection.close()
                        break

                    data_frame = DataFrame.from_bytes(data)

                    if data_frame.destination_address != self.address:
                        print(f"{self.index}. Destination address mismatch.")
                        self.connection.close()
                        break

                    payload = data_frame.payload
                    received_fcs = data_frame.fcs
                    self.payload_size = len(payload) * 8

                    if self.error_checker.validate(payload, received_fcs):
                        print(f"{self.index}. accepted")

                        ack_frame = ACK(
                            source_address=self.address,
                            destination_address=data_frame.source_address,
                            frame_seq_no=0
                        )
                        self.connection.sendall(ack_frame.to_bytes())

                        output.write(f"{self.index}. {payload}\n")
                        self.index += 1

                    else:
                        print(f"{self.index}. rejected")

                except Exception as e:
                    self.connection.close()
                    break

        self.validate_output()

    def validate_output(self):
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
