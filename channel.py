import random
from error_injector import inject_error_random
from dataframe import DataFrame

FRAME_LOSS_PROBABILITY=0.3
ERROR_PROBABILITY=0.3

class Channel:
    def __init__(self, frame_loss_prob=FRAME_LOSS_PROBABILITY, error_prob=ERROR_PROBABILITY):
        self.frame_loss_prob = frame_loss_prob
        self.error_prob = error_prob

    def transmit(self, dataframe):
        # Check if the input is an instance of DataFrame
        if not isinstance(dataframe, DataFrame):
            raise TypeError("Expected a DataFrame object")

        # Simulate frame loss
        if random.random() < self.frame_loss_prob:
            print("Frame lost during transmission.")
            return None  # Frame is lost

        # Simulate bit errors in the frame
        data_with_errors = self.introduce_errors(dataframe)
        return data_with_errors

    def introduce_errors(self, dataframe):
        if random.random() < self.error_prob:
            # Combine payload and FCS as a whole string
            combined_data = dataframe.payload + dataframe.fcs

            # Randomly choose the type of error to inject
            error_type = random.choice(["SINGLE", "DOUBLE", "ODD", "BURST"])

            if error_type == "BURST":
                max_burst_length = len(combined_data)
                if max_burst_length < 2:
                    burst_length = 1
                else:
                    burst_length = random.randint(2, max_burst_length)
                errored_data = inject_error_random(combined_data, error_type, burst_length=burst_length)
            else:
                errored_data = inject_error_random(combined_data, error_type)

            # Split the errored data back into payload and FCS
            new_payload = errored_data[:-32]  # All but the last 32 bits
            new_fcs = errored_data[-32:]      # Last 32 bits

            # Create a new DataFrame with the modified payload and FCS
            new_dataframe = DataFrame(
                source_address=dataframe.source_address,
                destination_address=dataframe.destination_address,
                length=dataframe.length,
                frame_seq_no=dataframe.frame_seq_no,
                payload=new_payload,
                error_checking_scheme=dataframe.error_checking_scheme
            )
            new_dataframe.fcs = new_fcs

            return new_dataframe
        return dataframe


# Example usage
if __name__ == "__main__":
    # Initialize the Channel with specific probabilities
    channel = Channel(frame_loss_prob=0.1, error_prob=0.05)

    # Example DataFrame creation
    src = b'\x01\x02\x03\x04\x05\x06'
    dst = b'\xaa\xbb\xcc\xdd\xee\xff'
    length = 64
    seq_no = 1
    payload = "11010110101101011010101101101010111111111"
    scheme = "CRC"

    # Create DataFrame instance
    df = DataFrame(src, dst, length, seq_no, payload, scheme)

    # Transmit the DataFrame through the channel
    transmitted_df = channel.transmit(df)

    if transmitted_df is None:
        print("Frame was lost.")
    else:
        print("Transmitted Payload:", transmitted_df.payload)
        print("Transmitted FCS:", transmitted_df.fcs)
