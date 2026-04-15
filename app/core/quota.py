from dataclasses import dataclass, field
from threading import Lock


@dataclass
class SlidingWindowState:
    budget_tokens: int
    window_seconds: int
    timestamps: list[int] = field(init=False)
    buckets: list[int] = field(init=False)
    running_total: int = 0
    lock: Lock = field(default_factory=Lock)
    last_updated_sec: int = 0

    def __post_init__(self) -> None:
        self.timestamps = [0] * self.window_seconds
        self.buckets = [0] * self.window_seconds

    def allow_and_reserve(self, now_sec: int, requested_tokens: int) -> tuple[bool, int, int]:
        with self.lock:
            if now_sec - self.last_updated_sec >= self.window_seconds:
                self.timestamps = [0] * self.window_seconds
                self.buckets = [0] * self.window_seconds
                self.running_total = 0

            slot = now_sec % self.window_seconds

            if self.timestamps[slot] != 0 and self.timestamps[slot] <= now_sec - self.window_seconds:
                self.running_total -= self.buckets[slot]
                self.timestamps[slot] = 0
                self.buckets[slot] = 0

            if self.running_total + requested_tokens > self.budget_tokens:
                return False, self.running_total, max(0, self.budget_tokens - self.running_total)

            if self.timestamps[slot] == now_sec:
                self.buckets[slot] += requested_tokens
            else:
                self.buckets[slot] = requested_tokens
                self.timestamps[slot] = now_sec

            self.running_total += requested_tokens
            self.last_updated_sec = now_sec

            return True, self.running_total, self.budget_tokens - self.running_total
