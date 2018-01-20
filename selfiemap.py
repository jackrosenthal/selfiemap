import threading
import random
import time
import requests
from math import sin, pi, cos
from sfml import sf
from queue import Queue, Empty

images_url = 'https://inmotion.adrivo.com/images/300/uploads/user/fcb/{}_preview.jpg'

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
        self.window.framerate_limit = 60
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
        downloader = SelfiesDownloader()
        downloader.daemon = True
        downloader.start()
        while True:
            t = sf.Texture.from_memory(downloader.q.get())
            spr = sf.Sprite(t)
            spr.origin = (x/2 for x in t.size)
            time.sleep(random.expovariate(10))
            w.q.put((random.uniform(-90, 90), random.uniform(-180, 180), spr))

class SelfiesDownloader(threading.Thread):
    def __init__(self):
        self.q = Queue()
        super().__init__()

    def run(self):
        while True:
            r = requests.get(images_url.format(random.choice(selfie_bits)))
            if not r.ok:
                print("WARNING: failed to download {}, HTTP Error {}".format(r.url, r.status_code))
                continue
            self.q.put(r.content)

if __name__ == '__main__':
    with open('data/images.lst') as f:
        selfie_bits = f.read().splitlines()
    w = Window()
    w.start()
    g = TestDataGenerator(w)
    g.daemon = True
    g.start()
    w.join()
