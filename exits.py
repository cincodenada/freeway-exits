import xml.etree.ElementTree as ET

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

        self.lanes = self.get_tag('lanes')
        self.lanedata = {}
        for key in self.lane_keys:
            lanedata = self.get_tag(key + ':lanes')
            self.lanedata[key] = lanedata.split('|') if lanedata else None

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

class Hwy:
    def __init__(self, starts, pool):
        self.starts = starts
        self.pool = pool
        self.add_segs()

    def add_segs(self):
        print(self.starts)
        for (start, id) in self.starts.items():
            self.add_seg(self.pool[id])

    def add_seg(self, seg):
        if(seg.end in self.starts):
            nextid = self.starts[seg.end]
            seg.next = self.pool[nextid]
            self.pool[nextid].prev = seg

# Get ways
nodes_to_hwy = {}
hwy_segs = {}
hwy_start = {}
links = {}
for way in root.iter('way'):
    seg = HwySeg(way)

    if(seg.type == 'motorway'):
        hwy_segs[seg.id] = seg
        if(seg.name not in hwy_start):
            hwy_start[seg.name] = {}

        hwy_start[seg.name][seg.start] = seg.id
    elif(seg.type == 'motorway_link'):
        links[seg.id] = seg

for (name, starts) in hwy_start.items():
    hwy = Hwy(starts, hwy_segs)
