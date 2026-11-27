import importlib.util
import json
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

MODULE_PATH = Path(__file__).resolve().parents[1] / "mock_server.py"
spec = importlib.util.spec_from_file_location("mock_server", MODULE_PATH)
mock_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock_server)


def start_server(scenario_name):
    scenarios = mock_server.load_scenarios(MODULE_PATH.with_name("scenarios.json"))
    server = mock_server.create_server(scenarios, scenario_name, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, "http://127.0.0.1:%d" % server.server_address[1]


def stop_server(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def get_json(url):
    with urlopen(url, timeout=2) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post_segment(base, data=b"test wav bytes"):
    request = Request(base + mock_server.SEGMENT_PATH, data=data, method="POST",
                      headers={"Content-Type": "audio/wav"})
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def test_health_has_explicit_stub_signature():
    server, thread, base = start_server("clean-turn")
    try:
        status, body = get_json(base + "/health")
        assert status == 200
        assert body["stub"] is True
        assert body["engine"] == "mock"
    finally:
        stop_server(server, thread)


def test_segment_returns_scripted_final_and_advanced_watermark():
    scenarios = {"test": {"events": [
        {"after_seconds": 0, "text": "scripted final", "final": True, "confidence": 0.9},
        {"after_seconds": 0, "text": "", "final": True, "confidence": 1.0, "turn_complete": True},
    ]}}
    server = mock_server.create_server(scenarios, "test", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    try:
        body = post_segment(base)
        events = body["results"]
        assert any(item["text"] == "scripted final" and item["final"] is True for item in events)
        assert any(item["turn_complete"] is True and item["turn_complete_watermark"] == 1 for item in events)
        timestamps = [item["capture_started_monotonic_ms"] for item in events]
        assert timestamps == sorted(timestamps)
    finally:
        stop_server(server, thread)


def test_results_endpoint_drains_pending_events():
    scenarios = {"test": {"events": [
        {"after_seconds": 0, "text": "partial", "final": False, "confidence": 0.5},
        {"after_seconds": 0.15, "text": "final", "final": True, "confidence": 0.9},
    ]}}
    server = mock_server.create_server(scenarios, "test", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    try:
        body = post_segment(base)
        assert [item["text"] for item in body["results"]] == ["partial"]
        time.sleep(0.2)
        status, drained = get_json(base + mock_server.RESULTS_PATH)
        assert status == 200
        assert [item["text"] for item in drained["results"]] == ["final"]
        status, empty = get_json(base + mock_server.RESULTS_PATH)
        assert status == 200
        assert empty["results"] == []
    finally:
        stop_server(server, thread)


def test_dies_scenario_stops_answering_health_probes():
    scenarios = {"test": {"server_dies_after_seconds": 0, "events": []}}
    server = mock_server.create_server(scenarios, "test", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    try:
        try:
            urlopen(base + "/health", timeout=2)
            assert False, "expected health probe to receive no HTTP response"
        except URLError:
            pass
    finally:
        stop_server(server, thread)
