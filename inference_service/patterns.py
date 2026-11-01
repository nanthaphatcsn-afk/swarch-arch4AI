"""Task 2 (cascade) and Task 3 (cached predictions). Your code goes here.

The inference service calls these when you switch the strategy to "cascade"
or turn the cache on (tools/loadtest.py does that for you).
"""
from collections import OrderedDict


# ---------------------------------------------------------------- Task 2
async def cascade(text, small, large, threshold):
    """Two-phase prediction: ask the small model first, and the large model only
    when the small one is not confident enough.

    small.predict(text)        -> Prediction, fast, call it normally
    await large.predict(text)  -> Prediction, slow, limited capacity
    A Prediction is a dict: {"label": ..., "confidence": 0.5-1.0, "model": ...}

    Return the small model's prediction if its confidence >= threshold,
    otherwise return the large model's prediction.
    """
    answer = small.predict(text)
    if answer["confidence"] >= threshold:
        return answer
    return await large.predict(text)


# ---------------------------------------------------------------- Task 3
class PredictionCache:
    """Cached predictions: remember answers for texts we have already seen.

    - Two texts that differ only in upper/lower case or extra spaces are the
      same entry ("Delicious!" and "  delicious! ").
    - Keep at most max_size entries; when full, evict the least recently used.
    - Count hits and misses (the service reports them in /metrics).

    Hint: an OrderedDict remembers insertion order; move_to_end(key) marks a key
    as recently used, and popitem(last=False) removes the oldest one.

    How the pieces fit: self._data maps key(text) -> Prediction. Keep it in
    order from least recently used (front) to most recently used (back).
    Then the entry to evict is always the one at the front.

        d = OrderedDict()
        d["a"] = 1; d["b"] = 2      # order: a, b
        d.move_to_end("a")          # order: b, a   ("a" was just used)
        d.popitem(last=False)       # removes "b", the least recently used

    Implement the three methods in order (key, get, put); get and put both
    start by calling self.key(text).

    Check: python -m pytest tests/test_task3_cache.py -v
    """

    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self._data = OrderedDict()

    @staticmethod
    def key(text):
        return " ".join(text.lower().split())

    def get(self, text):
        """Return the cached Prediction for text, or None. Count a hit or a miss."""
        key = self.key(text)
        if key in self._data:
            self._data.move_to_end(key)
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return None

    def put(self, text, prediction):
        """Store prediction for text; evict the least recently used entry when over max_size."""
        key = self.key(text)
        self._data[key] = prediction
        self._data.move_to_end(key)
        if len(self._data) > self.max_size:
            self._data.popitem(last=False)
