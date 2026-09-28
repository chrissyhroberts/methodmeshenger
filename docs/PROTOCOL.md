# MethodMeshenger wire protocol

The transport envelope is not the security protocol. Payload encryption,
identity binding and key lifecycle are defined separately in
[`SECURITY.md`](SECURITY.md).

## Design goals

The packet format must remain useful when MethodMeshenger grows from text to
attachments, voice and MethodMesh/ODK messages. It must also work within the
small ESP-NOW packet budget and remain understandable from a serial console.

The transport frame is therefore deliberately separate from its content:

- the envelope identifies the message, conversation, sender, recipient and
  delivery state;
- the content descriptor says whether the message is text, a file, voice or a
  control frame;
- the payload is either human-readable text or a bounded binary chunk;
- larger content is assembled from chunks using one message ID and chunk
  indexes.

MethodMeshenger nodes do not interpret application meaning. They transport
opaque content and delivery metadata.

## Version 1 envelope

The logical envelope is:

```json
{
  "protocol": "methodmeshenger",
  "version": 1,
  "message_id": "node-760216e0-00000001",
  "conversation_id": "conversation-01",
  "sender": "node-760216e0",
  "recipient": "node-76079130",
  "kind": "text",
  "encoding": "utf-8",
  "sequence": 1,
  "chunk_index": 0,
  "chunk_count": 1,
  "created_at_ms": 0,
  "expires_at_ms": 0,
  "ttl": 1,
  "metadata": "",
  "payload": "hello",
  "crc32": "00000000"
}
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `protocol` | Stable protocol family name. |
| `version` | Envelope version, independent of firmware version. |
| `message_id` | Globally unique logical message ID. Never reused. |
| `conversation_id` | Groups messages into a conversation or transfer. |
| `sender` / `recipient` | Application node IDs, not raw radio addresses. |
| `kind` | `text`, `attachment`, `voice`, `ack`, `control`, or future value. |
| `encoding` | `utf-8` for text or `base64` for binary chunks. |
| `sequence` | Sender sequence number for ordering and diagnostics. |
| `chunk_index` / `chunk_count` | Chunk position and total count. |
| `created_at_ms` / `expires_at_ms` | Optional sender timestamps. Zero means unknown. |
| `ttl` | Forwarding limit; the first direct implementation uses `1`. |
| `metadata` | Compact JSON descriptor for the content; empty for text and ACKs. |
| `payload` | Text or one bounded encoded chunk. |
| `crc32` | Integrity check over the canonical field list below. |

## Content kinds

### Text

`kind: "text"`, `encoding: "utf-8"`, with the text in `payload`.

### Attachment

The first chunk should carry a compact descriptor in a future `metadata`
field, for example media type, filename, byte length and content hash. The
actual bytes are chunked across subsequent frames. A complete attachment is
identified by the same `message_id`, not by a new message ID per chunk.
The descriptor is carried in `metadata` and must be identical on every chunk.

### Voice

Voice uses the same chunking mechanism. The descriptor should identify codec,
sample rate, channel count, duration and the complete-content hash. Live voice
and recorded voice should be distinct `kind` or mode values; they should not
be forced into the text-message path.

### Acknowledgements

An acknowledgement is a small envelope with `kind: "ack"` and a payload that
identifies the original `message_id`, the receiver and a status such as
`received`, `assembled` or `failed`. A radio-level send result is not an
application acknowledgement.

## Canonical integrity input

CRC must never be calculated from serialized JSON object order. Different
MicroPython runtimes may emit the same keys in different orders.

Version 1 calculates CRC32 over the UTF-8 bytes of these values joined with
`|`, in exactly this order:

```text
version|message_id|conversation_id|sender|recipient|kind|encoding|sequence|chunk_index|chunk_count|created_at_ms|expires_at_ms|ttl|metadata|payload
```

Missing optional values are represented by an empty string or `0` according to
their declared type. The `crc32` field itself is never included in the input.

## Packet-size rule

ESP-NOW packets have a bounded payload. The implementation must reserve room
for the envelope and leave a conservative maximum for `payload`; it must not
assume that a complete attachment or voice recording fits in one packet.

The chunking layer is therefore part of version 1, even if the initial UI only
uses one-chunk text messages.

## Compatibility rules

1. A receiver must ignore unknown fields.
2. A receiver must reject an unsupported `version` without crashing.
3. A receiver must deduplicate by `message_id` and `chunk_index`.
4. A receiver must not deliver incomplete attachments or voice content as if
   they were complete.
5. `@username` is resolved by a client directory before a frame is created;
   the wire recipient is a stable account/device route, not a mutable handle.
6. A future version must define a migration path rather than silently changing
   the meaning of an existing field.

## Current implementation gap

The first firmware slice currently implements the envelope only partially:
text, direct peer delivery, diagnostics, application ACKs and stable CRC are
present. The reference library also models chunking and content metadata;
attachment/voice transfer and durable node spooling remain planned firmware
work.
