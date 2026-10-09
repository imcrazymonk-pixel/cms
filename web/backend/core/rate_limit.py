"""Login rate limiting — mirrors Remnawave's login_guard concept.

In-memory sliding window keyed by client IP. No Redis required; state is
per-process (fine for a single API instance). After MAX_ATTEMPTS failed
logins within WINDOW seconds, further attempts are rejected with 429.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class LoginGuard:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._fails: Dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> None:
        q = self._fails[key]
        while q and now - q[0] > self.window:
            q.popleft()

    def is_blocked(self, key: str) -> bool:
        now = time.time()
        self._prune(key, now)
        return len(self._fails[key]) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        self._fails[key].append(time.time())

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)


login_guard = LoginGuard()
