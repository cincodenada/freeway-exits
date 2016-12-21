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

    def get_ang(self, node_pool, link_type, start_node = None):
        rev = (link_type == 'entrance')
        # Set default start_node depending on rev
        if(start_node is None):
            start_node = len(self.nodes)-1 if rev else 0

        if(len(self.nodes) >= 2):
            p = [node_pool[n] for n in (self.nodes[start_node:start_node-2:-1] if rev else self.nodes[start_node:start_node+2])]
            return math.atan2(p[1][0] - p[0][0], p[1][1] - p[0][1])
        else:
            return None

    def get_link_type(self, link):
        if((link.start in self.nodes) and (link.start != self.end)):
            return 'exit'
        elif((link.end in self.nodes) and (link.end != self.start)):
            return 'entrance'
        else:
            return None

    def get_rel_ang(self, node_pool, link):
        link_type = self.get_link_type(link)
        if(link_type is None):
            return None

        center_id = link.start if link_type == 'exit' else link.end
        start_node = self.nodes.index(center_id)
        diff = link.get_ang(node_pool, link_type) - self.get_ang(node_pool, link_type, start_node)

        if(abs(diff) == 180):
            raise ValueError("Exit 180 degrees from road!")

        if(abs(diff) > 180):
            diff -= math.copysign(360,diff)

        return diff

    def get_side(self, node_pool, link):
        type = self.get_link_type(link)
        if(type is None):
            return None
        else:
            rel_ang = self.get_rel_ang(node_pool, link)
            if(type == 'entrance'):
                return 'R' if rel_ang > 0 else 'L'
            else:
                return 'L' if rel_ang > 0 else 'R'


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
nodecoords = {int(n.get('id')): (float(n.get('lat')), float(n.get('lon'))) for n in root.iter('node')}

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

print(links[452336723].get_ang(nodecoords, True))
print(hwy_segs[4748960].get_ang(nodecoords, False))
print(links[436165683].get_ang(nodecoords, False))

# L
print(hwy_segs[452336740].get_side(nodecoords, links[452336723]))
# R
print(hwy_segs[4748960].get_side(nodecoords, links[436165683]))
# R
print(hwy_segs[428232211].get_side(nodecoords, links[96260970]))
# L
print(hwy_segs[14017470].get_side(nodecoords, links[85106512]))
# Breaks, not correct seg
print(hwy_segs[5130429].get_side(nodecoords, links[85106512]))

sys.exit()
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
