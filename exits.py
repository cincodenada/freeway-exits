import xml.etree.ElementTree as ET
import math

tree = ET.parse('motorway.osm')
root = tree.getroot()

class HwySeg:
    lane_keys = ['turn','hov','hgv','bus','motor_vehicle','motorcycle']
    def __init__(self, el):
        self.el = el

        self.id = int(self.el.attrib.get('id'))

        self.nodes = [int(sel.attrib.get('ref')) for sel in el.findall('nd')]
        self.start = self.nodes[0]
        self.end = self.nodes[-1]

        self.name = self.get_tag('ref')
        self.type = self.get_tag('highway')
        self.dest = self.get_tag('destination')

        try:
            self.lanes = int(self.get_tag('lanes'))
        except (TypeError, ValueError):
            self.lanes = 0
        self.lanedata = {}
        for key in self.lane_keys:
            lanedata = self.get_tag(key + ':lanes')
            self.lanedata[key] = lanedata.split('|') if lanedata else None

        self.prev = None
        self.next = None
        self.exits = []
        self.entrances = []

    def get_tag(self, k):
        tagel = self.el.find("./tag[@k='{}']".format(k))
        # I'm not sure why this is necessary?
        # Maybe it's not?
        if(hasattr(tagel, 'get')):
            return tagel.get('v')
        elif(hasattr(tagel, 'attrib')):
            return tagel.attrib.get('v')
        else:
            return None

    def get_ang(self, node_pool, rev=False):
        if(len(self.nodes) >= 2):
            p = [node_pool[n] for n in (self.nodes[-2:] if rev else self.nodes[:2])]
            return math.atan((p[1][1] - p[0][1])/(p[1][0]-p[0][0]))
        else:
            return None

class Hwy:
    def __init__(self, name, start_idx, end_idx, pool):
        self.name = name
        self.start_idx = start_idx
        self.end_idx = end_idx

        self.starts = []
        self.ends = []
        self.pool = pool

    def add_seg(self, seg):
        previd = nextid = None
        if(seg.end in self.start_idx):
            nextid = self.start_idx[seg.end]
            seg.next = self.pool[nextid]
        if(seg.start in self.end_idx):
            previd = self.end_idx[seg.start]
            seg.prev = self.pool[previd]

        if(previd and not nextid):
            self.ends.append(seg)
        elif(nextid and not previd):
            self.starts.append(seg)

    def add_link(self, link):
        if(link.start in self.end_idx):
            self.pool[self.end_idx[link.start]].exits.append(link)
        if(link.end in self.end_idx):
            self.pool[self.end_idx[link.end]].entrances.append(link)

class HwySet:
    def __init__(self, segs):
        self.hwys = {}
        self.segs = segs

    def add_hwy(self, name, starts, ends):
        self.hwys[name] = Hwy(name, starts, ends, self.segs)

    def add_seg(self, seg):
        self.hwys[seg.name].add_seg(seg)

    def add_link(self, link):
        for (name, hwy) in self.hwys.items():
            hwy.add_link(link)

    def get_hwy(self, name):
        return self.hwys[name]

# Get ways
nodes_to_hwy = {}
hwys = {}
hwy_segs = {}
hwy_names = set()
hwy_start = {}
hwy_end = {}
links = {}

print("Getting nodes...")
nodecoords = {int(n.get('id')): (float(n.get('lon')), float(n.get('lat'))) for n in root.iter('node')}

print("Getting ways...")
for way in root.iter('way'):
    seg = HwySeg(way)

    if(seg.type == 'motorway'):
        hwy_segs[seg.id] = seg

        hwy_names.add(seg.name)
        if(seg.name not in hwy_start):
            hwy_start[seg.name] = {}
        if(seg.name not in hwy_end):
            hwy_end[seg.name] = {}

        hwy_start[seg.name][seg.start] = seg.id
        hwy_end[seg.name][seg.end] = seg.id
    elif(seg.type == 'motorway_link'):
        links[seg.id] = seg

print("Analyzing...")

print(links[4755209].get_ang(nodecoords, True))
hwys = HwySet(hwy_segs)
for name in hwy_names:
    hwys.add_hwy(name, hwy_start[name], hwy_end[name])

for (id, seg) in hwy_segs.items():
    hwys.add_seg(seg)

for (id, link) in links.items():
    hwys.add_link(link)

for start in hwys.get_hwy('I 5').starts:
    curseg = start
    curlanes = start.lanes
    while curseg.next:
        if(curlanes != curseg.lanes or len(curseg.exits) or len(curseg.entrances)):
            lanes = 'H'*curlanes
            if(len(curseg.exits)):
                lanes += '-> ' + ';'.join([s.dest if s.dest else '???' for s in curseg.exits])
            if(len(curseg.entrances)):
                lanes += '<- ???'
            print(lanes)
            curlanes = curseg.lanes
        curseg = curseg.next
    print('H'*curlanes)
    print("---")
