import threading
import random
import time
import requests
from math import sin, pi, cos
from sfml import sf
from queue import Queue, Empty
from collections import defaultdict

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
            name, code, city, selfie = downloader.q.get()
            code = code.casefold()
            city = city.casefold()
            t = sf.Texture.from_memory(selfie)
            spr = sf.Sprite(t)
            spr.origin = (x/2 for x in t.size)
            time.sleep(random.expovariate(1))
            try:
                coord = cities[code][city]
            except KeyError:
                print("WARNING: I don't quite know where {}/{} is...".format(
                    code, city
                ))
                if cities.get(code):
                    coord = random.choice(list(cities.get(code).values()))
                else:
                    coord = (random.uniform(-90, 90), random.uniform(-180, 180))
            w.q.put(coord + (spr, ))

class SelfiesDownloader(threading.Thread):
    def __init__(self):
        self.q = Queue()
        super().__init__()

    def run(self):
        while True:
            selfie = random.choice(selfie_data)
            try:
                r = requests.get(images_url.format(selfie[3]))
            except requests.exceptions.ConnectionError:
                print("WARNING: connection error")
                continue
            if not r.ok:
                print("WARNING: failed to download {}, HTTP Error {}".format(r.url, r.status_code))
                continue
            self.q.put(tuple(selfie[:-1]) + (r.content, ))

if __name__ == '__main__':
    with open('data/images.csv') as f:
        selfie_data = [l.split(',') for l in f.read().splitlines()]
    cities = defaultdict(dict)
    with open('data/cities.csv') as f:
        for line in f:
            code, unaccent, accent, _, _, lati, longi = line.split(',')
            for name in unaccent, accent:
                cities[code.casefold()][name.casefold()] = tuple(map(float, (lati, longi)))
    w = Window()
    w.start()
    g = TestDataGenerator(w)
    g.daemon = True
    g.start()
    w.join()
