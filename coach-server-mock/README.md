# Mock ASR server — contract stub

> **WARNING: This is a stub. It returns scripted words from a scenario file, never transcribes audio, and its health signature is deliberately marked `"stub": true`. It must not be mistaken for a real transcription server.**

## Start it

You need Python 3; no packages need installing. Open a terminal in this folder and run:

```text
python mock_server.py
```

It listens only on this computer at `127.0.0.1:8765`. Stop it with Ctrl+C. To use a different built-in scenario:

```text
python mock_server.py --scenario slow-final
```

Available names: `clean-turn`, `slow-final`, `server-dies-mid-call`, and `static-segment`. Edit `scenarios.json` to change scripted words, confidence, or event timing without touching Python. Restart the server after editing. The optional `--port` flag changes the port while keeping the bind address loopback-only.

## What the server returns

- `GET /health` returns `{"stub":true,"engine":"mock","status":"ok"}` while healthy. In `server-dies-mid-call`, after five seconds from segment submission, the server closes health-probe connections without sending any HTTP response. The process remains running so pending scripted results can still be polled. The prompt requires a health route but does not specify its path; `/health` is an implementation choice.
- `POST /api/call-coach/asr/segment` consumes and discards the request body, then starts the selected script and returns due events in `{"results":[...]}`.
- `GET /api/call-coach/results` returns events whose scheduled times have arrived. Returned events are drained and will not be returned again.

Each scripted event uses `text`, `final`, `confidence`, `capture_started_monotonic_ms`, `capture_ended_monotonic_ms`, `turn_complete`, and `turn_complete_watermark`. The watermark increments when a turn-complete event is emitted. Timestamps are monotonic-clock values in milliseconds, not wall-clock dates.

## Use it with the page

Start the server, choose a scenario, and open the Live Seller Coach page configured to use this local server. A successful seam should show the page recognizing the mock health signature, submitting a segment, displaying scripted transcript events, and updating turn-complete state when the watermark arrives. If the page rejects the health response or does not show results, the interface contract needs confirmation. Do not remove the stub markers to make it look like a real server.

The slow-final scenario emits a partial immediately and schedules its final 15 seconds later. The dies-mid-call scenario makes health connections receive no response after the five-second threshold; it does not terminate the process. The static scenario returns empty transcript text with low confidence.

## Unverified contract details

The supplied contract does not establish the health route path, the JSON envelope for segment/results responses, or exact field names/types for timestamps and the turn-complete watermark. The implementation therefore uses `/health`; a `results` array envelope; event fields `text` (string), `final` (boolean), `confidence` (number), `capture_started_monotonic_ms` and `capture_ended_monotonic_ms` (numbers), `turn_complete` (boolean), and `turn_complete_watermark` (integer). These names/types are **UNVERIFIED** against the page's actual interface. The server implements only the named health, segment, and results routes; other paths receive 404. It makes no external network calls.

Uploaded bytes are read and discarded; the server does not retain audio. Do not send sensitive recordings to this stub.
