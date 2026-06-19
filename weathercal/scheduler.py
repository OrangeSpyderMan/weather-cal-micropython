from .compat import ticks_add, ticks_diff


class PageScheduler:
    def __init__(self, pages, default_duration_s, now_ms):
        self.pages = pages
        self.default_duration_s = default_duration_s
        self.index = 0
        self.paused = False
        self.deadline = self._deadline(now_ms)

    @property
    def page(self):
        return self.pages[self.index]

    def update(self, now_ms):
        if self.paused or ticks_diff(now_ms, self.deadline) < 0:
            return False
        self.index = (self.index + 1) % len(self.pages)
        self.deadline = self._deadline(now_ms)
        return True

    def next(self, now_ms):
        self.index = (self.index + 1) % len(self.pages)
        self.deadline = self._deadline(now_ms)

    def previous(self, now_ms):
        self.index = (self.index - 1) % len(self.pages)
        self.deadline = self._deadline(now_ms)

    def home(self, now_ms):
        self.index = 0
        self.deadline = self._deadline(now_ms)

    def toggle_pause(self, now_ms):
        self.paused = not self.paused
        self.deadline = self._deadline(now_ms)

    def _deadline(self, now_ms):
        seconds = self.page.get("duration_s", self.default_duration_s)
        return ticks_add(now_ms, int(seconds * 1000))
