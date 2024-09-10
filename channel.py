import random
from error_injector import inject_error_random
from dataframe import DataFrame

FRAME_LOSS_PROBABILITY = 0.3
ERROR_PROBABILITY = 0.3

class Channel:
    def __init__(self, frame_loss_prob=FRAME_LOSS_PROBABILITY, error_prob=ERROR_PROBABILITY):
        self.frame_loss_prob = frame_loss_prob
        self.error_prob = error_prob
        print(f"frame_loss_prob={frame_loss_prob}")
        print(f"error_prob={error_prob}")

    def transmit(self, dataframe):
        if not isinstance(dataframe, DataFrame):
            raise TypeError("Expected a DataFrame object")

        if random.random() < self.frame_loss_prob:
            print("Frame lost during transmission.")
            return None

        data_with_errors = self.introduce_errors(dataframe)
        return data_with_errors

    def introduce_errors(self, dataframe):
        if random.random() < self.error_prob:
            combined_data = dataframe.payload + dataframe.fcs
            error_type = random.choice(["SINGLE", "DOUBLE", "ODD", "BURST"])

            if error_type == "BURST":
                max_burst_length = len(combined_data)
                burst_length = 1 if max_burst_length < 2 else random.randint(2, max_burst_length)
                errored_data = inject_error_random(combined_data, error_type, burst_length=burst_length)
            else:
                errored_data = inject_error_random(combined_data, error_type)

            new_payload = errored_data[:-32]
            new_fcs = errored_data[-32:]

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