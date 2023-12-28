from collections import namedtuple
from typing import Union
import binascii
import struct
import time
from functools import partial
import zipfile
from os import remove

Token = namedtuple("Token", ["offset", "length", "indicator"])


def compress(
    input_string: str, max_offset: int = 2047, max_length: int = 31
) -> list[Token]:
    output = []
    input_idx = 0
    input_string = memoryview(input_string.encode("ascii"))
    total_len = len(input_string)
    while input_idx < total_len:
        length, offset = best_length_offset(
            input_string[:input_idx],
            input_string[input_idx:],
            max_length,
            max_offset,
        )
        output.append(Token(offset, length, input_string[input_idx]))
        input_idx += length
    return output


def best_length_offset(
    window: memoryview,
    input_string: memoryview,
    max_length: int = 31,
    max_offset: int = 4095,
) -> tuple[int, int]:
    w_len = len(window)
    length, offset = 2, 0
    ip_str_0 = input_string[0]
    rl = partial(run_length, window, input_string, len(input_string), w_len)
    for found_length, index in [
        (rl(w_len - i), i)
        for i in range(1, (min(w_len, max_offset) + 1))
        if window[-i] == ip_str_0
    ]:
        if max_length > found_length > length:
            length, offset = found_length, index
    return (length, offset) if length > 2 else (1, 0)


def run_length(
    window: memoryview,
    input_string: memoryview,
    i_len: int,
    w_len: int,
    start_idx: int,
) -> int:
    count = 0
    window_size = w_len - start_idx
    while (
        count < i_len
        and window[start_idx + (count % window_size)] == input_string[count]
    ):
        count += 1
    return count


def huff_codes(val: Union[int, str]) -> tuple[int, int]:
    if isinstance(val, str):  # Literal byte
        val = ord(val)
    if val < 144:
        return int(bin(val + 0b00110000), 2), 8
    elif val < 257:
        return int(bin(val - 144 + 0b110010000), 2), 9
    elif val < 280:
        return int(bin(val - 257 + 0b0010100), 2), 7
    elif val < 288:
        return int(bin(val - 280 + 0b11000000), 2), 8
    else:
        return None


def length_code(n: int) -> tuple[int, int, int]:
    if n <= 2:
        return n, 0, 0
    if n <= 10:
        return 254 + n, 0, 0
    elif n <= 18:
        return 265 + (n - 11) // 2, (n - 11) % 2, 1
    elif n <= 34:
        return 269 + (n - 19) // 4, (n - 19) % 4, 2
    elif n <= 66:
        return 273 + (n - 35) // 8, (n - 35) % 8, 3
    elif n <= 130:
        return 277 + (n - 67) // 16, (n - 67) % 16, 4
    elif n < 258:
        return 281 + (n - 131) // 32, (n - 131) % 32, 5
    elif n == 258:
        return 285, 0, 0
    else:
        return None


def distance_code(n: int) -> tuple[int, int, int]:
    if n <= 4:
        return n - 1, 0, 0
    elif n <= 8:
        return (n - 5) // 2 + 4, (n - 5), 1
    elif n <= 16:
        return (n - 9) // 4 + 6, (n - 9), 2
    elif n <= 32:
        return (n - 17) // 8 + 8, (n - 17), 3
    elif n <= 64:
        return (n - 33) // 16 + 10, (n - 33), 4
    elif n <= 128:
        return (n - 65) // 32 + 12, (n - 65), 5
    elif n <= 256:
        return (n - 129) // 64 + 14, (n - 129), 6
    elif n <= 512:
        return (n - 257) // 128 + 16, (n - 257), 7
    elif n <= 1024:
        return (n - 513) // 256 + 18, (n - 513), 8
    elif n <= 2048:
        return (n - 1025) // 512 + 20, (n - 1025), 9
    elif n <= 4096:
        return (n - 2049) // 1024 + 22, (n - 2049), 10
    elif n <= 8192:
        return (n - 4097) // 2048 + 24, (n - 4097), 11
    elif n <= 16384:
        return (n - 8193) // 4096 + 26, (n - 8193), 12
    elif n <= 32768:
        return (n - 16385) // 8192 + 28, (n - 16385), 13
    else:
        return None


def tokens_to_stream(compressed: list[Token]) -> bytes:
    it = "110"
    for tok in compressed:
        if tok.length <= 1:
            # Write a literal
            code, shift = huff_codes(tok.indicator)
            it += f"{code:0{shift}b}"
        else:
            # Length/distance pair, write `nbits` bits with value `ebits` in reverse order
            code, ebits, nbits = length_code(tok.length)
            it += f"{code:07b}"[-7:]
            if nbits >= 1:
                it += f"{ebits:0{nbits}b}"[-nbits:][::-1]
            code, ebits, nbits = distance_code(tok.offset)
            it += f"{code:05b}"[-5:]
            if nbits >= 1:
                it += f"{ebits:0{nbits}b}"[-nbits:][::-1]
    # Pad to byte boundary, add terminating byte
    return (
        b"".join(
            [
                int(it[i : i + 8][::-1], 2).to_bytes(1, byteorder="big", signed=False)
                for i in range(0, len(it), 8)
            ]
        )
        + b"\x00"
    )


def string_to_zip(filename: str, strk: str) -> None:
    compressed = compress(strk)
    bitstream_bytes = tokens_to_stream(compressed)
    filename_bytes = filename.encode("ascii")
    filename_len = len(filename_bytes)
    mod_time = time.localtime()
    # DOS time and date calculations
    dos_time = (mod_time.tm_year - 1980) << 9 | mod_time.tm_mon << 5 | mod_time.tm_mday
    dos_date = mod_time.tm_hour << 11 | mod_time.tm_min << 5 | mod_time.tm_sec // 2

    crc_val = binascii.crc32(strk.encode("ascii"))
    uncomp_size = len(strk.encode("ascii"))
    comp_size = len(bitstream_bytes)
    # Create the local file header
    local_header = (
        b"PK\003\004"
        + struct.pack(
            "<2B4HL2L2H",
            20,
            20,
            0,
            8,
            dos_time,
            dos_date,
            crc_val,
            comp_size,
            uncomp_size,
            filename_len,
            0,
        )
        + filename_bytes
    )

    # Create the central directory header
    cd_header = b"PK\001\002" + struct.pack(
        "<4B4HL2L5H2L",
        20,
        20,
        20,
        20,
        0,
        8,
        dos_time,
        dos_date,
        crc_val,
        comp_size,
        uncomp_size,
        filename_len,
        0,
        0,
        0,
        0,
        0x20,
        0,
    )
    cd_header += filename_bytes

    # Create the end of central directory record
    end_of_cd_record = struct.pack(
        "<4s4H2LH",
        b"PK\x05\x06",  # signature
        0,  # number of this disk
        0,  # disk where cd starts
        1,
        1,  # number of entries in the cd on this disk and total
        len(cd_header),  # size of the central directory
        len(local_header) + comp_size,  # offset of start of central directory
        0,  # comment length
    )

    # Concatenate all pieces to form the ZIP file content
    zip_content = local_header + bitstream_bytes + cd_header + end_of_cd_record
    with open("sample.zip", "wb") as f:
        f.write(zip_content)


uncompressed_string = """"Did you win your sword fight?"
            "Of course I won the fucking sword fight," Hiro says. "I'm the greatest sword fighter in the world."
            "And you wrote the software."
            "Yeah. That, too," Hiro says.",
        """


string_to_zip(
    "sample.txt",
    uncompressed_string,
)
f = open("sample.zip", "rb")
z = zipfile.ZipFile(f)
assert z.namelist() == ["sample.txt"]
assert z.read("sample.txt") == uncompressed_string.encode("ascii")
remove("sample.zip")
