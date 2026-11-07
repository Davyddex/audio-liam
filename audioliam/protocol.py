"""Length-prefixed PCM audio frames sent over a TCP stream."""
import struct

_HEADER = struct.Struct("!I")
MAX_FRAME_BYTES = 1024 * 1024


def encode_frame(payload: bytes) -> bytes:
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError("audio frame is too large")
    return _HEADER.pack(len(payload)) + payload


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
    (size,) = _HEADER.unpack(header)
    if size > MAX_FRAME_BYTES:
        raise ValueError("peer sent an oversized audio frame")
    return recv_exact(sock, size)
