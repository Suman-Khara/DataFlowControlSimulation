WINDOW_SIZE = 3
TIMEOUT = 4

import threading
import socket
from channel import Channel
from dataframe import DataFrame
from ackframe import ACK
from error_checker import CRC, Checksum
import traceback
import time

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
        self.sent_frames = {}  
        self.base = 0  
        self.next_seq_num = 0  
        self.timer = None  

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
        start_time=time.time()
        while True:
            eof_reached = False  
            
            while self.next_seq_num < self.base + self.window_size:
                dataframe = self.makeDataFrame(self.next_seq_num)
                if dataframe is None:
                    eof_reached = True  
                    break  
               
                self.sent_frames[self.next_seq_num] = dataframe
                self.send_frame(dataframe)

                if self.base == self.next_seq_num:
                    self.start_timer()  

                self.next_seq_num += 1

           
            if eof_reached and self.base == self.next_seq_num:
                print("All frames sent and acknowledged. Transmission complete.")
                end_time = time.time()
                total_time = end_time - start_time
                print(f"Total transmission time: {total_time:.2f} seconds")
                break
                   
            self.receive_ack()

    def send_frame(self, dataframe):
        transmitted_frame = self.channel.transmit(dataframe)
        if transmitted_frame:
            log_action = f"{dataframe.frame_seq_no}. Sent\n"
            with open(self.log_file, 'a') as log:
                log.write(log_action)
            self.connection.send(transmitted_frame.to_bytes())
            print(f"Frame {dataframe.frame_seq_no} sent to channel.")

    def start_timer(self):
        self.timer = threading.Timer(self.timeout, self.timeout_handler)
        self.timer.start()

    def stop_timer(self):
        if self.timer:
            self.timer.cancel()

    def timeout_handler(self):
        print(f"Timeout occurred. Resending frames from {self.base}.")
        
        for seq_no in range(self.base, self.next_seq_num):
            self.send_frame(self.sent_frames[seq_no])

     
        self.start_timer()

    def receive_ack(self):
        try:
            ack_frame = self.connection.recv(1024) 
            ack = ACK.from_bytes(ack_frame)

            if ack.frame_seq_no >= self.base:
                print(f"ACK {ack.frame_seq_no} received.")
               
                self.base = ack.frame_seq_no + 1

                if self.base == self.next_seq_num:
                    self.stop_timer()  
                else:
                    self.start_timer() 

           
            if ack.frame_seq_no == self.next_seq_num - 1:
                print("All frames acknowledged. Stopping the timer.")
                self.stop_timer()

        except socket.error as e:
            print(f"Socket error while receiving ACK: {e}")

class Receiver:
    def __init__(self, connection, checker, address, input_file='input.txt', output_file="output.txt"):
        self.connection = connection
        self.input_file = input_file
        self.output_file = output_file
        if checker == 'CRC':
            self.error_checker = CRC()
        elif checker == 'Checksum':
            self.error_checker = Checksum()
        self.expected_seq_num = 0 
        self.address = address

    def receive_data(self):
        with open(self.output_file, 'w') as output:
            while True:
                try:
                    data = self.connection.recv(1024)
                    if not data:
                        print("Connection closed by sender.")
                        self.connection.close()
                        break

                    data_frame = DataFrame.from_bytes(data)
                    if data_frame.destination_address != self.address:
                        print(f"Frame {data_frame.frame_seq_no} Destination address mismatch.")
                        continue

                    payload = data_frame.payload
                    received_fcs = data_frame.fcs
                    frame_seq_no = data_frame.frame_seq_no
                    self.payload_size = len(payload) * 8
                    
                    if self.error_checker.validate(payload, received_fcs):
                        if frame_seq_no == self.expected_seq_num:
                            print(f"Frame {frame_seq_no} accepted")
                            output.write(f"{frame_seq_no}. {payload}\n")
                            self.expected_seq_num += 1
                            ack_frame = ACK(
                                source_address=self.address,
                                destination_address=data_frame.source_address,
                                frame_seq_no=frame_seq_no
                            )
                            self.connection.sendall(ack_frame.to_bytes())
                        else:
                            print(f"Frame {frame_seq_no} discarded (out of order)")

                    else:
                        print(f"Frame {frame_seq_no} rejected (FCS error)")

                except Exception as e:
                    print(f"Error receiving data: {e}")
                    traceback.print_exc() 
                    self.connection.close()
                    break
        self.validate_output()        
                
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
