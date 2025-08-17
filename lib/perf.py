from time import perf_counter
from typing import Union


def output_perf(func):
    def warp(*args, **kwargs):
        counter = Counter()
        result = func(*args, **kwargs)
        print(counter.endT())
        return result

    return warp


class FPSMonitor:
    def __init__(self, cnt_times: int = 90):
        self.count_times = cnt_times
        self.fps_list = []
        self.fps_count = 0
        self.last_output = perf_counter()
        self.last_count = perf_counter()

    @property
    def fps(self):
        return sum(self.fps_list) / self.fps_count

    def count(self):
        crt_time = perf_counter()

        self.fps_list.append(1 / (crt_time - self.last_count))
        self.last_count = crt_time

        self.fps_count += 1
        if self.fps_count > self.count_times:
            self.fps_count -= 1
            self.fps_list.pop(0)

        if crt_time - self.last_output > 1.0:
            self.last_output = crt_time
            print(f"{self.fps:.2f}")


class Counter:
    def __init__(self, create_start: bool = False):
        self.timers = {}
        self.results = {}
        self.local_timer = perf_counter()

    def start(self, *names: str) -> Union[None, 'Counter']:
        if names:
            for name in names:
                self.timers[name] = perf_counter()
            return None
        else:
            self.local_timer = perf_counter()
            return self

    def end(self, name: str | None = None) -> float:
        if name in self.timers:
            self.results[name] = perf_counter() - self.timers.pop(name)
            return self.results[name]
        elif name in self.results:
            return self.results[name]
        elif name is None:
            temp = perf_counter() - self.local_timer
            self.local_timer = 0
            return temp
        else:
            raise KeyError(f"Timer {name} does not exist")

    def endT(self, name: str | None = None):
        ret = self.end(name)
        return f"{ret * 1000:.3f} ms"

    def __str__(self):
        return "\n".join(
            f"{n}: {v * 1000:.3f} ms" for n, v in {**self.results, "##Local##": self.local_timer}.items()
        )
