import threading
import random
import time
from math import sin, pi, cos
from sfml import sf
from queue import Queue, Empty

def latpx(lat, scale):
    return (-lat + 90) / 180 * scale

def lonpx(lon, scale):
    return (lon + 180) / 360 * scale

class Window(threading.Thread):
    def __init__(self):
        texture = sf.Texture.from_file("map.png")
        self.world = sf.Sprite(texture)
        self.size = texture.size
        self.window = sf.RenderWindow(sf.VideoMode(*self.size), "SelfieMap")
        self.q = Queue()
        self.objects = []
        super().__init__()

    def run(self):
        while self.window.is_open:
            for event in self.window.events:
                if event.type == event.CLOSED:
                    self.window.close()
                if event.type == event.KEY_PRESSED and event['code'] == 16:
                    self.window.close()
            self.window.clear()
            self.window.draw(self.world)
            while True:
                try:
                    lati, longi, obj = self.q.get_nowait()
                    obj.position = (
                        f(c, s) for f, c, s in zip((lonpx, latpx),
                                                   (longi, lati),
                                                   tuple(self.size))
                    )
                    self.objects.append((obj, 0))
                except Empty:
                    break
            for obj, clock in self.objects:
                scale = sin(clock/200 * pi)
                obj.ratio = scale, scale
                self.window.draw(obj)
            self.objects = [(o, c + 1) for o, c in self.objects if c < 200]
            self.window.display()

class TestDataGenerator(threading.Thread):
    def __init__(self, w):
        self.w = w
        super().__init__()

    def run(self):
        r = sf.RectangleShape((100, 100))
        r.fill_color = sf.Color(255, 255, 0, 255)
        r.origin = 50, 50
        w.q.put((39.746944, -105.210833, r))
        while True:
            time.sleep(random.expovariate(10))
            r = sf.RectangleShape((100, 100))
            r.fill_color = sf.Color(*([random.randint(0, 255) for _ in range(3)] + [255]))
            r.origin = 50, 50
            w.q.put((random.uniform(-90, 90), random.uniform(-180, 180), r))

if __name__ == '__main__':
    w = Window()
    w.start()
    g = TestDataGenerator(w)
    g.daemon = True
    g.start()
    w.join()
