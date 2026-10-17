from backend.app import config
from backend.app.bus import EventBus
from backend.tools.make_samples import samples


def test_bounded_cache_sequence_and_since():
    bus = EventBus()
    state,_ = samples()
    sequence = [bus.publish_state(state)["seq"]]
    for i in range(600):
        sequence.append(bus.publish_event("network_changed",{"network":"online"},i)["seq"])
    assert sequence == list(range(1,602))
    assert len(bus.events) == 500
    assert len(bus.since(599)) == 2


def test_slow_client_cannot_block_publisher():
    bus = EventBus()
    queue = bus.subscribe()
    for _ in range(config.WS_QUEUE_SIZE+1):
        bus.publish_event("network_changed",{"network":"online"},0)
    assert queue not in bus.connections
    assert queue.get_nowait() is None
