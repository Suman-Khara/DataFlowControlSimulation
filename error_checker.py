CRC_POLYNOMIALS = {
    "CRC-32": "100000100110000010001110110110111"
}


def xor(a, b):
    result = []
    for i in range(1, len(b)):
        result.append('0' if a[i] == b[i] else '1')
    return ''.join(result)


def mod2div(dividend, divisor):
    pick = len(divisor)
    tmp = dividend[0:pick]
    while pick < len(dividend):
        if tmp[0] == '1':
            tmp = xor(divisor, tmp) + dividend[pick]
        else:
            tmp = xor('0' * pick, tmp) + dividend[pick]
        pick += 1
    if tmp[0] == '1':
        tmp = xor(divisor, tmp)
    else:
        tmp = xor('0' * pick, tmp)
    return tmp


class CRC:
    def __init__(self, crc_type="CRC-32"):
        self.crc_type = crc_type
        self.polynomial = CRC_POLYNOMIALS[crc_type]

    def generate_fcs(self, dataword):
        l_key = len(self.polynomial)
        appended_data = dataword + '0' * (l_key - 1)
        remainder = mod2div(appended_data, self.polynomial)
        return remainder

    def validate(self, dataword, fcs):
        codeword = dataword + fcs
        remainder = mod2div(codeword, self.polynomial)
        return remainder.count('1') == 0


class Checksum:
    def __init__(self, size=32):
        self.size = size

    def generate_fcs(self, dataword):
        padded_dataword = dataword.ljust(
            (len(dataword) + self.size - 1) // self.size * self.size, '0')
        chunks = [padded_dataword[i:i + self.size]
                  for i in range(0, len(padded_dataword), self.size)]
        return self.generate_checksum(chunks)

    def generate_checksum(self, chunks):
        res = 0
        for chunk in chunks:
            res += int(chunk, 2)
        res_bin = bin(res)[2:].zfill(self.size)
        while len(res_bin) > self.size:
            carry = res_bin[:-self.size]
            res_bin = res_bin[-self.size:]
            res_bin = bin(int(res_bin, 2) + int(carry, 2))[2:].zfill(self.size)
        return ''.join('1' if x == '0' else '0' for x in res_bin)

    def validate(self, dataword, fcs):
        padded_dataword = dataword.ljust(
            (len(dataword) + self.size - 1) // self.size * self.size, '0')
        chunks = [padded_dataword[i:i + self.size]
                  for i in range(0, len(padded_dataword), self.size)]
        return self.check_checksum(chunks, fcs)

    def check_checksum(self, chunks, checksum):
        res = 0
        for chunk in chunks:
            res += int(chunk, 2)
        res += int(checksum, 2)
        res_bin = bin(res)[2:].zfill(self.size)
        while len(res_bin) > self.size:
            carry = res_bin[:-self.size]
            res_bin = res_bin[-self.size:]
            res_bin = bin(int(res_bin, 2) + int(carry, 2))[2:].zfill(self.size)
        return all(bit == '1' for bit in res_bin)