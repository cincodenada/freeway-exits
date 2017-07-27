import math
import sys
from collections import defaultdict, deque

class Node:
    def __init__(self, xmlobj):
        self.id = int(xmlobj.get('id'))
        self.lat = float(xmlobj.get('lat'))
        self.lon = float(xmlobj.get('lon'))
        try:
            nodetype = xmlobj.find("./tag[@k='highway']").get('v')
            if(nodetype == 'motorway_junction'):
                self.name = xmlobj.find("./tag[@k='ref']").get('v')
            else:
                self.name = None
        except AttributeError:
            self.name = None

class Network:
    def __init__(self, osmTree):
        self.xml = osmTree
        self.nodes = {}
        self.hwys = {}
        self.links = SegIndex()
        self.link_entrances = SegIndex()
        self.hwy_names = set()
        self.hwy_segs = SegIndex('get_hwys', merge=True)

        self.parseNodes()
        self.parseWays()

        self.hwys = HwySet(self.hwy_segs, self.links)
        for name in self.hwy_names:
            self.hwys.add_hwy(name)

        for seg in self.hwy_segs.segs.values():
            self.hwys.add_seg(seg)

    def parseNodes(self):
        print("Getting nodes...", file=sys.stderr)
        for n in self.xml.iter('node'):
            curnode = Node(n)
            self.nodes[curnode.id] = curnode

    def parseWays(self):
        print("Getting ways...", file=sys.stderr)
        for way in self.xml.iter('way'):
            try:
                if(way.find("./tag[@k='oneway']").get('v') != 'yes'):
                    continue
            except AttributeError:
                continue

            seg = HwySeg(way, self.nodes)

            if(seg.type == 'motorway'):
                self.hwy_segs.add(seg)
                for name in seg.get_hwys():
                    self.hwy_names.add(name)
            elif(seg.type == 'motorway_link'):
                self.links.add(seg)

    def parseAuxWays(self, osmTree):
        for way in osmTree.iter('way'):
            curseg = HwySeg(way, None)
            way_id = int(way.get('id'))
            for ndref in way.findall("./nd"):
                n_id = int(ndref.get('ref'))
                seg_id = self.links.lookup(n_id, 'start')
                if(seg_id and seg_id != way_id):
                    end_link = self.links.lookup_end(seg_id, 'end')
                    print("Matched entrance link {} to segment {} from {} via node {}".format(way_id, end_link.id, seg_id, n_id))
                    end_link.dest = curseg.get_tag('name', 'ref')


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
        if(not self.dest):
            self.dest = self.get_tag('destination:ref')

        self.add_lanes = 0
        self.remove_lanes = 0

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
        self.links = []

    def get_hwys(self):
        if(self.name):
            return self.name.split(';')
        else:
            return [None]

    def describe_link(self, trunk):
        link_type = trunk.get_link_type(self)
        dest = self.dest if self.dest else '???'
        if(link_type == 'exit'):
            side = trunk.get_side(self)
            return '{}: {}'.format(self.get_number(), dest)
        else:
            return dest

    def get_number(self):
        return self.node_pool[self.start].name

    def get_tag(self, *args):
        for k in args:
            tagel = self.el.find("./tag[@k='{}']".format(k))
            # I'm not sure why this is necessary?
            # Maybe it's not?
            if(hasattr(tagel, 'get')):
                return tagel.get('v')
            elif(hasattr(tagel, 'attrib')):
                return tagel.attrib.get('v')

        return None

    def get_ang(self, link_type, start_node = None):
        rev = (link_type == 'entrance')
        # Set default start_node depending on rev
        if(start_node is None):
            start_node = len(self.nodes)-1 if rev else 0

        end_node = start_node-2 if rev else start_node+2
        step = -1 if rev else 1
        # Deal with list[1:-1:-1] not working as expected
        if end_node == -1:
            end_node = None

        if(len(self.nodes) >= 2):
            p = [self.node_pool[n] for n in self.nodes[start_node:end_node:step]]
            return math.atan2(p[1].lon - p[0].lon, p[1].lat - p[0].lat)
        else:
            return None


    def get_link_type(self, link):
        if((link.start in self.nodes) and (link.start != self.end)):
            return 'exit'
        elif((link.end in self.nodes) and (link.end != self.start)):
            return 'entrance'
        else:
            print(link.start, link.end)
            print(self.nodes)
            return None

    def get_rel_ang(self, link):
        link_type = self.get_link_type(link)
        if(link_type is None):
            return None

        center_id = link.start if link_type == 'exit' else link.end
        start_node = self.nodes.index(center_id)
        diff = link.get_ang(link_type) - self.get_ang(link_type, start_node)

        if(abs(diff) == math.radians(180)):
            raise ValueError("Exit 180 degrees from road!")

        if(abs(diff) > math.radians(180)):
            diff -= math.copysign(math.radians(360),diff)

        return diff

    def get_side(self, link):
        type = self.get_link_type(link)
        if(type is None):
            return None
        else:
            rel_ang = self.get_rel_ang(link)
            if(type == 'exit'):
                return 1 if rel_ang > 0 else -1
            else:
                return -1 if rel_ang > 0 else 1

    def add_exit(self, link):
        self.links.append(link)

    def add_entrance(self, link):
        self.links.append(link)

class Exit(HwySeg):
    pass

class Entrance(HwySeg):
    pass

class Hwy:
    def __init__(self, name, parent):
        self.name = name

        self.starts = []
        self.ends = []
        self.parent = parent

    def add_seg(self, seg):
        nextid = self.lookup(seg.end, 'start')
        if(nextid):
            seg.next = self.parent.segs.get(nextid)
        previd = self.lookup(seg.start, 'end')
        if(previd):
            seg.prev = self.parent.segs.get(previd)

        if(previd and not nextid):
            self.ends.append(seg)
        elif(nextid and not previd):
            self.starts.append(seg)

        seg.links = []
        for l in self.parent.links.lookup_all(seg.nodes):
            link = self.parent.links.get(l[1])
            if link.start != seg.end and link.end != seg.start:
                seg.links.append(l)

    def lookup(self, seg_id, idx):
        return self.parent.segs.lookup(seg_id, idx, self.name)

    def dump_entrance_nodes(self):
        nodes = set()
        for start in self.starts:
            curseg = start
            while(curseg):
                for (t, id) in curseg.links:
                    if(t == 'entrance'):
                        link = self.parent.links.lookup_end(id, 'start')
                        print(link.start)
                curseg = curseg.next

class HwySet:
    def __init__(self, segs, links):
        self.hwys = {}
        self.segs = segs
        self.links = links

    def add_hwy(self, name):
        self.hwys[name] = Hwy(name, self)

    def add_seg(self, seg):
        for name in seg.get_hwys():
            self.hwys[name].add_seg(seg)

    def add_link(self, link):
        for (name, hwy) in self.hwys.items():
            hwy.add_link(link)

    def get_hwy(self, name):
        return self.hwys[name]

    def dump_entrance_nodes(self):
        for hwy in self.hwys.values():
            hwy.dump_entrance_nodes()

class SegIndex:
    no_seg = '_all_'

    def __init__(self, partition_by = None, merge = False):
        self.segs = {}
        self.indexes = {
            'start': defaultdict(dict),
            'end': defaultdict(dict),
        }
        self.partition_by = partition_by
        self.merge = merge

    def get(self, id):
        return self.segs[id]

    def add(self, seg):
        self.segs[seg.id] = seg

        for idx_key in self.indexes:
            if(self.partition_by):
                for val in self.get_partitions(seg):
                    self.add_to_idx(idx_key, seg, part_val=val)
            else:
                self.add_to_idx(idx_key, seg)

    def get_partitions(self, seg):
        part_val = getattr(seg, self.partition_by)
        if(callable(part_val)):
            return part_val()
        else:
            return [part_val]

    def add_to_idx(self, idx_key, seg, part_val=None):
        if not part_val:
            part_val = self.no_seg

        cur_idx = self.indexes[idx_key][part_val]

        key = getattr(seg, idx_key)
        if(self.merge):
            try:
                # Deal with merges/splits, widest gets priority
                prevseg = self.get(cur_idx[key])
                if(seg.lanes > prevseg.lanes):
                    seg = self.merge_lanes(seg, prevseg, idx_key)
                else:
                    seg = self.merge_lanes(prevseg, seg, idx_key)
            except KeyError:
                pass

        cur_idx[key] = seg.id

    # TODO: Do we need to worry about segments in the middle here?
    def merge_lanes(self, main, branch, merge_point):
        branch.discard = True
        if(merge_point == 'start'):
            # Start of split lanes, add all previous lanes to our additional lanes
            main.add_lanes = branch.lanes + branch.add_lanes
        else:
            # End of split, we're downsizing
            main.remove_lanes = branch.lanes + branch.remove_lanes

        return main

    def lookup(self, node_id, idx, partition=None):
        if not partition:
            partition = self.no_seg

        node_id = int(node_id)
        lookup = self.indexes[idx][partition]

        if(node_id in lookup):
            return lookup[node_id]
        else:
            return None

    def lookup_all(self, node_ids, partition = None):
        matches = []
        for node_id in node_ids:
            for idx_type in self.indexes.keys():
                link_type = 'exit' if idx_type == 'start' else 'entrance'

                seg_id = self.lookup(node_id, idx_type, partition)
                if(seg_id):
                    matches.append((link_type, seg_id))

        return matches

    def lookup_end(self, link_id, direction, maxloop = 100):
        relattr = 'start' if direction == 'end' else 'end'
        last_ids = deque(maxlen=20)
        numloops = 0
        while(link_id):
            last_ids.append(link_id)
            cur_link = self.get(link_id)
            cur_node = getattr(cur_link, relattr)
            print("Looking for {} of segment {} at {}...".format(direction, link_id, cur_node))
            link_id = self.lookup(getattr(cur_link, direction), relattr)
            numloops+=1
            if(numloops > maxloop):
                print("I seem to have found a loop...", file=sys.stderr)
                print(last_ids, file=sys.stderr)
                break

        return cur_link
