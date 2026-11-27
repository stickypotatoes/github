#!/usr/bin/env python3
"""Loopback-only scripted ASR contract stub; never performs transcription."""

import argparse
import heapq
import json
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SEGMENT_PATH = "/api/call-coach/asr/segment"
RESULTS_PATH = "/api/call-coach/results"
# The prompt requires a health route but does not state its path.
HEALTH_PATH = "/health"


def load_scenarios(path):
    with Path(path).open("r", encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), dict):
        raise ValueError("scenario file must contain an object named 'scenarios'")
    return data["scenarios"]


class ScenarioState:
    def __init__(self, scenarios, selected):
        if selected not in scenarios:
            raise ValueError("unknown scenario: " + selected)
        self.scenarios = scenarios
        self.selected = selected
        self.pending = []
        self.sequence = 0
        self.watermark = 0
        self.started_at = None
        self.dead_after = scenarios[selected].get("server_dies_after_seconds")
        self.lock = Lock()

    def start_segment(self):
        now = time.monotonic()
        scenario = self.scenarios[self.selected]
        with self.lock:
            self.started_at = now
            self.watermark = 0
            self.pending.clear()
            for event in scenario.get("events", []):
                delay = float(event.get("after_seconds", 0))
                self.sequence += 1
                heapq.heappush(self.pending, (now + delay, self.sequence, dict(event)))
            return self._drain_due(now)

    def _drain_due(self, now):
        ready = []
        while self.pending and self.pending[0][0] <= now:
            due, _sequence, event = heapq.heappop(self.pending)
            if event.get("turn_complete") is True:
                self.watermark += 1
            # Event field names are stub choices where the page's exact schema
            # is not specified in the supplied contract.
            ready.append({
                "text": event.get("text", ""),
                "final": bool(event.get("final", False)),
                "confidence": float(event.get("confidence", 0.0)),
                "capture_started_monotonic_ms": due * 1000.0,
                "capture_ended_monotonic_ms": due * 1000.0,
                "turn_complete": bool(event.get("turn_complete", False)),
                "turn_complete_watermark": self.watermark,
            })
        return ready

    def poll(self):
        with self.lock:
            return self._drain_due(time.monotonic())

    def health_is_dead(self):
        with self.lock:
            return (self.started_at is not None and self.dead_after is not None
                    and time.monotonic() - self.started_at >= float(self.dead_after))


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _json(self, status, payload):
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == HEALTH_PATH:
                if state.health_is_dead():
                    # Intentionally send no HTTP status or body: the probe gets
                    # a closed connection, not a degraded-health response.
                    self.close_connection = True
                    try:
                        self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    self.connection.close()
                    return
                self._json(200, {"stub": True, "engine": "mock", "status": "ok"})
                return
            if self.path == RESULTS_PATH:
                self._json(200, {"results": state.poll()})
                return
            self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != SEGMENT_PATH:
                self._json(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0:
                    raise ValueError("negative content length")
                # Consume and immediately discard upload bytes; no audio is retained.
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except (ValueError, OSError):
                self._json(400, {"error": "invalid upload"})
                return
            self._json(200, {"results": state.start_segment()})

        def log_message(self, _format, *_args):
            return

    return Handler


def create_server(scenarios, selected, port=DEFAULT_PORT):
    server = ThreadingHTTPServer((DEFAULT_HOST, port), make_handler(ScenarioState(scenarios, selected)))
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description="Loopback scripted ASR contract stub")
    parser.add_argument("--scenario", default="clean-turn", help="scenario name from scenarios.json")
    parser.add_argument("--scenario-file", default=str(Path(__file__).with_name("scenarios.json")))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    scenarios = load_scenarios(args.scenario_file)
    server = create_server(scenarios, args.scenario, args.port)
    print("Mock ASR stub (not a transcription engine) listening at http://127.0.0.1:" + str(args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
