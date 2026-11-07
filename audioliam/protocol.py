"""Control handshake and length-prefixed, sequenced PCM frames."""
import struct

HELLO = b"ALM1"
READY = b"ALR1"
BUSY = b"ALB1"
_HEADER = struct.Struct("!II")  # payload length, frame sequence
MAX_FRAME_BYTES = 1024 * 1024


def encode_frame(payload: bytes, sequence: int) -> bytes:
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError("audio frame is too large")
    return _HEADER.pack(len(payload), sequence & 0xFFFFFFFF) + payload


def recv_exact(sock, size: int):
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            return None
        chunks.extend(chunk)
    return bytes(chunks)


def recv_frame(sock):
    header = recv_exact(sock, _HEADER.size)
    if header is None:
        return None
    size, sequence = _HEADER.unpack(header)
    if size > MAX_FRAME_BYTES:
        raise ValueError("peer sent an oversized audio frame")
    payload = recv_exact(sock, size)
    if payload is None:
        return None
    return sequence, payload
