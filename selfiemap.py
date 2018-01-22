import threading
import random
import time
import requests
import bottle
from math import sin, pi, cos
from sfml import sf
from queue import Queue, Empty
from collections import defaultdict

images_url = 'https://inmotion.adrivo.com/images/300/uploads/user/fcb/{}_preview.jpg'

class Window(threading.Thread):
    def __init__(self):
        self.loading_text = sf.Text('Initializing...')
        self.loading_text.character_size = 64
        self.loading_text.font = sf.Font.from_file('loading.ttf')
        self.texture = sf.Texture.from_file("data/world16384.png")
        self.world = sf.Sprite(self.texture)
        self.video_mode = sf.VideoMode.get_fullscreen_modes()[0]
        vm_size = self.video_mode.width, self.video_mode.height
        self.world.origin = (c / 2 for c in self.texture.size)
        self.world.position = (c / 2 for c in vm_size)
        self.world.ratio = (min(v / t for t, v in zip(self.texture.size, vm_size)) ,) * 2
        self.original_ratio = self.world.ratio.x
        self.fc_logo = sf.Sprite(sf.Texture.from_file("fcbayern.png"))
        self.fc_logo.origin = 200, 400
        self.fc_logo.position = vm_size[0] / 2, vm_size[1] / 2 - 30
        self.dhl = sf.Sprite(sf.Texture.from_file("globalfamily.png"))
        self.dhl.origin = self.dhl.texture.size
        self.dhl.position = (x - 60 for x in vm_size)
        self.loading_text.position = vm_size[0] / 2, vm_size[1] / 2 + 30
        self.loading_text.color = sf.Color(255, 255, 255, 255)
        self.fade = sf.RectangleShape(vm_size)
        self.fade.fill_color = sf.Color(0, 0, 0, 200)
        self.fade.position = (0, 0)
        self.window = sf.RenderWindow(self.video_mode, "FanMap")
        self.window.framerate_limit = 60
        self.q = Queue()
        self.objects = []
        self.zoomt = -1
        self.zoomdirec = 0
        self.target_origin = self.world.origin
        super().__init__()

    def win_to_lcoord(self, winc):
        gb = self.world.global_bounds
        return ((scrn - world) / self.world.ratio.x
                for scrn, world in zip(winc, (gb.left, gb.top)))

    def lcoord_to_win(self, lc):
        gb = self.world.global_bounds
        return (l * self.world.ratio.x + world
                for l, world in zip(lc, (gb.left, gb.top)))

    def run(self):
        while self.window.is_open:
            self.world.origin = ((0.5 * t + 1.5 * z)/2 for t, z in zip(self.target_origin, self.world.origin))
            if self.zoomt >= 0:
                self.zoomt += 1
                df = self.zoomdirec * 0.006 * sin(pi / 200 * self.zoomt + pi/2)
                self.world.ratio = (x + df for x in self.world.ratio)
                if self.world.ratio.x <= 0.5*self.original_ratio:
                    self.zoomt = -1
                    continue
                if self.zoomt == 100:
                    self.zoomt = -1
            for event in self.window.events:
                if event.type == event.CLOSED:
                    self.window.close()
                if event.type == event.KEY_PRESSED and event['code'] == 16:
                    self.window.close()
                if ((event.type == event.KEY_PRESSED and event['code'] == sf.Keyboard.SPACE)
                    or (event.type == event.MOUSE_BUTTON_PRESSED and event['button'] == 1)):
                    self.zoomdirec = -1
                    self.zoomt = 0
                    if self.world.ratio.x <= self.original_ratio:
                        self.target_origin = tuple(c / 2 for c in self.texture.size)
                if event.type == event.MOUSE_BUTTON_PRESSED and event['button'] == 0:
                    self.zoomdirec = 1
                    point = event['x'], event['y']
                    if self.world.global_bounds.contains(point):
                        self.target_origin = tuple(self.win_to_lcoord(point))
                    self.zoomdirec = 1
                    self.zoomt = 0
            self.window.clear()
            self.window.draw(self.world)
            self.window.draw(self.dhl)
            if self.loading_text.string:
                self.window.draw(self.fade)
                lb = self.loading_text.local_bounds
                self.loading_text.origin = lb.width / 2, lb.height / 2
                self.window.draw(self.loading_text)
                self.window.draw(self.fc_logo)
            else:
                while True:
                    try:
                        lati, longi, obj = self.q.get_nowait()
                        obj.position = self.lcoord_to_win(
                                f(c) for f, c in zip((self.lonpx, self.latpx),
                                                    (longi, lati))
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

    def latpx(self, lat):
        return (-lat + 90) / 180 * self.texture.size.y

    def lonpx(self, lon):
        return (lon + 180) / 360 * self.texture.size.x

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

class BottleDataProvider(threading.Thread):
    def __init__(self, w):
        self.w = w
        super().__init__()

    def run(self):
        app = bottle.app()

        @app.post('/selfie')
        def selfie():
            r = requests.get(bottle.request.POST['image_url'])
            gps = (48.1500, 11.5833)
            t = sf.Texture.from_memory(r.content)
            spr = sf.Sprite(t)
            spr.origin = (x / 2 for x in t.size)
            self.w.q.put(gps + (spr, ))

        app.run(host='0.0.0.0', port='8080')

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

class DataLoader(threading.Thread):
    def run(self):
        global selfie_data
        global cities
        cities = defaultdict(dict)
        w.loading_text.string = 'Loading Test Data...'
        with open('data/images.csv') as f:
            selfie_data = [l.split(',') for l in f.read().splitlines()]
        w.loading_text.string = 'Loading City Data...'
        with open('data/cities.csv') as f:
            for line in f:
                code, unaccent, accent, _, _, lati, longi = line.split(',')
                for name in unaccent, accent:
                    cities[code.casefold()][name.casefold()] = tuple(map(float, (lati, longi)))
        w.loading_text.string = ''

if __name__ == '__main__':
    w = Window()
    w.start()
    loader = DataLoader()
    loader.start()
    loader.join()
    ws = BottleDataProvider(w)
    ws.daemon = True
    ws.start()
    g = TestDataGenerator(w)
    g.daemon = True
    g.start()
    w.join()
