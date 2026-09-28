"""MethodMeshenger v0.1: the smallest useful ESP-NOW chat node.

Serial input is broadcast over ESP-NOW. Received frames are printed as JSON.
This deliberately has no BLE, provisioning, encryption or MethodMesh code.
"""

import json
import time
from machine import unique_id

import network
import espnow
import wire


NODE_ID = "node-" + "".join("%02x" % byte for byte in unique_id()[-4:])
BROADCAST = b"\xff\xff\xff\xff\xff\xff"
NODE_1_MAC = b"\x44\xb1\x76\x02\x16\xe0"
NODE_2_MAC = b"\x44\xb1\x76\x07\x91\x30"
MAX_PAYLOAD = 180
RADIO_CHANNEL = 6
seen = []
inbox = []
sequence = 0


def emit(event, **body):
    record = {"event": event, "node_id": NODE_ID, "ts_ms": time.ticks_ms()}
    record.update(body)
    print(json.dumps(record))


def mac_text(mac):
    return ":".join("%02x" % byte for byte in mac)


def make_frame(text):
    global sequence
    sequence += 1
    now_ms = time.ticks_ms()
    message_id = NODE_ID + "-" + str(now_ms) + "-" + str(sequence)
    conversation_id = NODE_ID + ":" + mac_text(peer_mac)
    return wire.text_frame(NODE_ID, mac_text(peer_mac), sequence, message_id, conversation_id, text[:MAX_PAYLOAD], now_ms)


def serial_frame(line):
    """Accept a client-shaped frame, while keeping plain text convenient."""
    try:
        candidate = json.loads(line)
        if wire.valid(candidate):
            return candidate
    except Exception:
        pass
    return make_frame(line)


def remember(message_id, chunk_index):
    key = (message_id, chunk_index)
    if key in seen:
        return False
    seen.append(key)
    del seen[:-128]
    return True


def json_packets(raw):
    """Yield complete JSON objects from padded or concatenated radio bytes."""
    start = -1
    depth = 0
    quoted = False
    escaped = False
    index = 0
    while index < len(raw):
        value = raw[index]
        if start < 0:
            if value == 123 or value == b"{":
                start = index
                depth = 1
            index += 1
            continue
        if quoted:
            if escaped:
                escaped = False
            elif value == 92 or value == b"\\":
                escaped = True
            elif value == 34 or value == b'"':
                quoted = False
        elif value == 34 or value == b'"':
            quoted = True
        elif value == 123 or value == b"{":
            depth += 1
        elif value == 125 or value == b"}":
            depth -= 1
            if depth == 0:
                yield raw[start:index + 1]
                start = -1
        index += 1


def process_incoming(host, raw):
    if raw is None:
        return
    emit("received_raw", peer=mac_text(host), bytes=len(raw))
    # ESP-NOW v2 can expose a fixed-size buffer containing one or more padded
    # payloads. Recover complete objects without trusting the buffer boundary.
    for packet in json_packets(raw):
        try:
            frame = json.loads(packet.decode())
            if not wire.valid(frame):
                emit("invalid", peer=mac_text(host), frame=frame, expected_crc=wire.checksum(frame), received_crc=frame.get("crc32"))
            elif remember(frame["message_id"], frame.get("chunk_index", 0)):
                if frame.get("kind") == "ack":
                    emit("ack_received", frame=frame, peer=mac_text(host), channel=RADIO_CHANNEL)
                else:
                    emit("message", frame=frame, peer=mac_text(host), channel=RADIO_CHANNEL)
                    try:
                        radio.add_peer(host, channel=RADIO_CHANNEL)
                    except Exception:
                        pass
                    ack = wire.ack_frame(NODE_ID, frame.get("sender", mac_text(host)), frame["message_id"], frame.get("conversation_id", ""), time.ticks_ms())
                    ack_sent = radio.send(host, json.dumps(ack).encode(), True)
                    emit("ack_sent", ack_for=frame["message_id"], peer=mac_text(host), radio_ok=ack_sent)
        except Exception as error:
            emit("error", stage="receive", detail=str(error), peer=mac_text(host))


def setup_radio():
    # ESP-NOW peers must share the same Wi-Fi channel. Reset both virtual
    # interfaces so a previous soft-reset or Wi-Fi connection cannot leave a
    # board on an unexpected channel.
    wlan = network.WLAN(network.WLAN.IF_STA)
    network.WLAN(network.WLAN.IF_AP).active(False)
    wlan.active(False)
    wlan.active(True)
    try:
        wlan.disconnect()
    except Exception:
        pass
    wlan.config(channel=RADIO_CHANNEL)
    try:
        wlan.config(pm=wlan.PM_NONE)
    except Exception:
        pass
    radio = espnow.ESPNow()
    radio.active(True)
    local_mac = wlan.config("mac")
    peer_mac = NODE_2_MAC if local_mac == NODE_1_MAC else NODE_1_MAC
    peer_registered = False
    try:
        radio.add_peer(peer_mac, channel=RADIO_CHANNEL)
        peer_registered = True
    except Exception:
        pass
    return radio, local_mac, peer_mac, peer_registered


radio, local_mac, peer_mac, peer_registered = setup_radio()
emit("ready", mode="unicast", local_mac=mac_text(local_mac), peer=mac_text(peer_mac), peer_registered=peer_registered, channel=RADIO_CHANNEL, max_payload=MAX_PAYLOAD)


def radio_receive_callback(radio_instance):
    while True:
        host, raw = radio_instance.irecv(0)
        if host is None:
            return
        # Keep the IRQ callback short. JSON parsing and radio.send() can block
        # and must happen in the normal interpreter loop, not in the ESP-NOW
        # interrupt context.
        if len(inbox) < 32:
            inbox.append((host, raw))


radio.irq(radio_receive_callback)

while True:
    try:
        while inbox:
            host, raw = inbox.pop(0)
            process_incoming(host, raw)
        import uselect
        poll = uselect.poll()
        poll.register(__import__("sys").stdin, uselect.POLLIN)
        if poll.poll(0):
            line = __import__("sys").stdin.readline().strip()
            if line:
                frame = serial_frame(line)
                sent = radio.send(peer_mac, json.dumps(frame).encode(), True)
                emit("sent", frame=frame, local_mac=mac_text(local_mac), peer=mac_text(peer_mac), peer_registered=peer_registered, radio_ok=sent, configured_channel=RADIO_CHANNEL, live_channel=network.WLAN(network.WLAN.IF_STA).config("channel"))
    except Exception as error:
        emit("error", stage="send", detail=str(error))

    time.sleep_ms(20)
