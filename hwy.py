import math

class Node:
    def __init__(self, xmlobj):
        self.id = int(xmlobj.get('id'))
        self.lat = float(xmlobj.get('lat'))
        self.lon = float(xmlobj.get('lon'))
        type = xmlobj.find('./tag[@k="highway"]')
        if(type == 'motorway_junction'):
            self.name = xmlobj.find('./tag[@k="ref"]').get('v')
        else:
            self.name = None

class HwySeg:
    lane_keys = ['turn','hov','hgv','bus','motor_vehicle','motorcycle']

    def __init__(self, el, node_pool):
        self.el = el
        self.node_pool = node_pool

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

    def describe_link(self, trunk):
        fromto = 'to' if trunk.get_link_type(self) == 'exit' else 'from'
        side = trunk.get_side(self)
        dest = self.dest if self.dest else '???'
        return '{} {} {}'.format(self.name, fromto, dest, side)

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

    def get_ang(self, link_type, start_node = None):
        rev = (link_type == 'entrance')
        # Set default start_node depending on rev
        if(start_node is None):
            start_node = len(self.nodes)-1 if rev else 0

        if(len(self.nodes) >= 2):
            p = [self.node_pool[n] for n in (self.nodes[start_node:start_node-2:-1] if rev else self.nodes[start_node:start_node+2])]
            return math.atan2(p[1].lon - p[0].lon, p[1].lat - p[0].lat)
        else:
            return None


    def get_link_type(self, link):
        if((link.start in self.nodes) and (link.start != self.end)):
            return 'exit'
        elif((link.end in self.nodes) and (link.end != self.start)):
            return 'entrance'
        else:
            return None

    def get_rel_ang(self, link):
        link_type = self.get_link_type(link)
        if(link_type is None):
            return None

        center_id = link.start if link_type == 'exit' else link.end
        start_node = self.nodes.index(center_id)
        diff = link.get_ang(link_type) - self.get_ang(link_type, start_node)

        if(abs(diff) == 180):
            raise ValueError("Exit 180 degrees from road!")

        if(abs(diff) > 180):
            diff -= math.copysign(360,diff)

        return diff

    def get_side(self, link):
        type = self.get_link_type(link)
        if(type is None):
            return None
        else:
            rel_ang = self.get_rel_ang(link)
            if(type == 'exit'):
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
        if(link.start in self.start_idx):
            self.pool[self.start_idx[link.start]].exits.append(link)
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
