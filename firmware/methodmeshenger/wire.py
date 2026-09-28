"""MicroPython-compatible MethodMeshenger v1 wire helpers."""

import binascii


PROTOCOL = "methodmeshenger"
VERSION = 1
CRC_FIELDS = ("version", "message_id", "conversation_id", "sender", "recipient", "kind", "encoding", "sequence", "chunk_index", "chunk_count", "created_at_ms", "expires_at_ms", "ttl", "metadata", "payload")


def _value(frame, field):
    value = frame.get(field, "")
    return "" if value is None else str(value)


def checksum(frame):
    raw = "|".join(_value(frame, field) for field in CRC_FIELDS).encode()
    return "%08x" % (binascii.crc32(raw) & 0xffffffff)


def text_frame(node_id, recipient, sequence, message_id, conversation_id, payload, now_ms):
    frame = {
        "protocol": PROTOCOL,
        "version": VERSION,
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender": node_id,
        "recipient": recipient,
        "kind": "text",
        "encoding": "utf-8",
        "sequence": sequence,
        "chunk_index": 0,
        "chunk_count": 1,
        "created_at_ms": now_ms,
        "expires_at_ms": 0,
        "ttl": 1,
        "metadata": "",
        "payload": payload,
    }
    frame["crc32"] = checksum(frame)
    return frame


def ack_frame(node_id, recipient, ack_for, conversation_id, now_ms):
    frame = {
        "protocol": PROTOCOL,
        "version": VERSION,
        "message_id": ack_for + ":ack:" + node_id,
        "conversation_id": conversation_id,
        "sender": node_id,
        "recipient": recipient,
        "kind": "ack",
        "encoding": "utf-8",
        "sequence": 0,
        "chunk_index": 0,
        "chunk_count": 1,
        "created_at_ms": now_ms,
        "expires_at_ms": 0,
        "ttl": 1,
        "metadata": "",
        "payload": ack_for,
    }
    frame["crc32"] = checksum(frame)
    return frame


def valid(frame):
    return (
        isinstance(frame, dict)
        and frame.get("protocol") == PROTOCOL
        and frame.get("version") == VERSION
        and isinstance(frame.get("message_id"), str)
        and isinstance(frame.get("sender"), str)
        and isinstance(frame.get("recipient"), str)
        and frame.get("kind") in ("text", "attachment", "voice", "ack", "control")
        and frame.get("crc32") == checksum(frame)
    )
