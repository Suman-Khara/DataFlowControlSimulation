import threading
import time
import socket
from channel import Channel
from dataframe import DataFrame
from ackframe import ACK
from error_checker import CRC, Checksum

WINDOW_SIZE=4
TIMEOUT = 2

class Sender:
    def __init__(self, connection, input_file, source, destination, checker, bytes, window_size=WINDOW_SIZE, log_file="log.txt"):
        self.connection = connection
        self.input_file = input_file
        self.source_address = source
        self.destination_address = destination
        self.error_checker = checker
        self.channel = Channel()
        self.payload_size = bytes
        self.log_file = log_file
        self.lock = threading.Lock()
        self.window_size = window_size
        self.base = 0
        self.next_frame_to_send = 0
        self.frame_buffer = {}
        self.acknowledged = {}
        self.timer = None
        self.timer_lock = threading.Lock()
        self.stop_sending = False

    def makeDataFrame(self, frame_number):
        start_char_index = frame_number * self.payload_size * 8
        num_chars_to_read = self.payload_size * 8

        with open(self.input_file, 'r') as input:
            input.seek(start_char_index)
            data = input.read(num_chars_to_read)
            
            if not data:
                return None  # End of file reached

        dataframe = DataFrame(self.source_address, self.destination_address, self.payload_size, frame_number, data, self.error_checker)
        return dataframe

    def send_data(self):
        with open(self.log_file, 'w'):
            pass

        ack_thread = threading.Thread(target=self.receive_ack)
        ack_thread.start()

        while not self.stop_sending:
            with self.lock:
                while self.next_frame_to_send < self.base + self.window_size and not self.stop_sending:
                    dataframe = self.makeDataFrame(self.next_frame_to_send)

                    if dataframe is None:
                        self.stop_sending = True
                        break

                    transmitted_df = self.channel.transmit(dataframe)

                    if transmitted_df:
                        data_to_send = transmitted_df.to_bytes()
                        self.connection.sendall(data_to_send)
                        self.log(f"Frame {self.next_frame_to_send} sent")

                    self.frame_buffer[self.next_frame_to_send] = dataframe
                    self.acknowledged[self.next_frame_to_send] = False

                    if self.base == self.next_frame_to_send:
                        self.start_timer()

                    self.next_frame_to_send += 1

                if self.stop_sending and self.base == self.next_frame_to_send:
                    break

        ack_thread.join()
        self.connection.close()

    def receive_ack(self):
        while not self.stop_sending:
            try:
                ack_data = self.connection.recv(1024)
                if ack_data:
                    ack = ACK.from_bytes(ack_data)
                    with self.lock:
                        if ack.ack_number in self.acknowledged:
                            self.acknowledged[ack.ack_number] = True
                            self.log(f"ACK {ack.ack_number} received")

                            while self.acknowledged.get(self.base, False):
                                self.base += 1
                                self.acknowledged.pop(self.base - 1, None)
                                self.frame_buffer.pop(self.base - 1, None)
                            
                            if self.base != self.next_frame_to_send:
                                self.start_timer()
                            else:
                                self.stop_timer()

            except socket.timeout:
                print("Timeout waiting for ACK")

    def start_timer(self):
        self.stop_timer()
        self.timer = threading.Timer(TIMEOUT, self.timeout_action)
        self.timer.start()

    def stop_timer(self):
        with self.timer_lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None

    def timeout_action(self):
        with self.lock:
            print(f"Timeout for frame {self.base}. Retransmitting frames from {self.base} to {self.next_frame_to_send - 1}")
            for i in range(self.base, self.next_frame_to_send):
                if not self.acknowledged.get(i, True):
                    dataframe = self.frame_buffer[i]
                    transmitted_df = self.channel.transmit(dataframe)
                    if transmitted_df:
                        data_to_send = transmitted_df.to_bytes()
                        self.connection.sendall(data_to_send)
                        self.log(f"Frame {i} re-sent")

            self.start_timer()

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
        self.expected_frame = 0
        self.address = address

    def receive_data(self):
        with open(self.output_file, 'w'):
            pass

        while True:
            try:
                data = self.connection.recv(1024)

                if not data:
                    print("Connection closed by client.")
                    self.connection.close()
                    break

                data_frame = DataFrame.from_bytes(data)

                if data_frame.destination_address != self.address:
                    print("Destination address mismatch. Closing connection.")
                    self.connection.close()
                    break

                payload = data_frame.payload
                received_fcs = data_frame.fcs
                frame_seq_no = data_frame.frame_seq_no
                payload_size = len(payload) * 8

                if self.error_checker.validate(payload, received_fcs):
                    if frame_seq_no == self.expected_frame:
                        print(f"Frame {frame_seq_no} accepted")
                        self.write_output(payload, self.expected_frame)

                        ack_frame = ACK(
                            source_address=self.address,
                            destination_address=data_frame.source_address,
                            frame_seq_no=self.expected_frame
                        )
                        self.connection.sendall(ack_frame.to_bytes())

                        self.expected_frame += 1

                    else:
                        print(f"Frame {frame_seq_no} out of order, expected {self.expected_frame}")
                        ack_frame = ACK(
                            source_address=self.address,
                            destination_address=data_frame.source_address,
                            frame_seq_no=self.expected_frame - 1
                        )
                        self.connection.sendall(ack_frame.to_bytes())

                else:
                    print(f"Frame {frame_seq_no} rejected due to FCS mismatch")

            except Exception as e:
                print(f"Error receiving data: {e}")
                self.connection.close()
                break

        self.validate_output(payload_size)

    def write_output(self, payload, index):
        with open(self.output_file, 'a') as output:
            output.write(f"{index + 1}. {payload}\n")

    def validate_output(self, payload_size):
        with open(self.input_file, 'r') as input_file, open(self.output_file, 'r+') as output_file:
            input_data = input_file.read().strip()
            output_lines = output_file.readlines()

            output_file.seek(0)

            for index, line in enumerate(output_lines):
                start = index * payload_size // 8
                end = (index + 1) * payload_size // 8
                if end > len(input_data):
                    break

                expected_payload = input_data[start:end]
                line_payload = line.strip().split('. ')[1]

                if line_payload != expected_payload:
                    output_file.write(f"{line.strip()} (incorrect)\n")
                else:
                    output_file.write(line)

            output_file.truncate()