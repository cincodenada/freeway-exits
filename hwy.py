import math
import sys
from collections import defaultdict

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
        self.hwy_segs = SegIndex(merge=True)

        self.parse_nodes()
        self.parse_ways()

        self.link_ways()

        self.hwys = HwySet(self.hwy_segs)

    def parse_nodes(self):
        print("Getting nodes...", file=sys.stderr)
        for n in self.xml.iter('node'):
            curnode = Node(n)
            self.nodes[curnode.id] = curnode

    def parse_ways(self):
        print("Getting ways...", file=sys.stderr)
        for way in self.xml.iter('way'):
            try:
                if(way.find("./tag[@k='oneway']").get('v') != 'yes'):
                    continue
            except AttributeError:
                continue

            seg_type = way.find("./tag[@k='highway']").get('v')
            if(seg_type == 'motorway'):
                self.hwy_segs.add(HwySeg(way, self.nodes))
            elif(seg_type == 'motorway_link'):
                self.links.add(LinkSeg(way, self.nodes))

    def parse_aux_ways(self, osmTree):
        for way in osmTree.iter('way'):
            newseg = HwySeg(way, None)
            for n_id in newseg.nodes:
                match_id = self.links.lookup(n_id, 'start')
                if(match_id and match_id != newseg.id):
                    end_link = self.links.lookup_end(match_id, 'end')
                    print("Matched entrance link {} to segment {} from {} via node {}".format(newseg.id, end_link.id, match_id, n_id))
                    end_link.dest_links[newseg.id] = newseg

    def link_ways(self):
        for s in self.hwy_segs.segs.values():
            s.update_links(self.hwy_segs, self.links)

        for s in self.links.segs.values():
            s.update_links(self.hwy_segs, self.links)


class Seg:
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

    def get_hwys(self):
        if(self.name):
            return self.name.split(';')
        else:
            return [None]

    def is_end(self):
        return (self.prev and not self.next)

    def is_start(self):
        return (self.next and not self.prev)

    def is_link(self):
        return (self.type == 'motorway_link')

    def update_links(self, hwyIndex, linkIndex):
        myIndex = linkIndex if self.is_link() else hwyIndex
        self.next = myIndex.lookup_seg(self.end, 'start')
        self.prev = myIndex.lookup_seg(self.start, 'end')

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

    # Calculate the absolute angle of this element
    # In a direction (forward or rev) from a given pivot node
    # Pivot node defaults to start/end for forward/rev
    def get_ang(self, rev, pivot_node = None):
        # Set pivot node depending on rev
        if not pivot_node:
            pivot_node = len(self.nodes)-1 if rev else 0

        end_node = pivot_node-2 if rev else pivot_node+2
        step = -1 if rev else 1
        # Deal with list[1:-1:-1] not working as expected
        if end_node == -1:
            end_node = None

        if(len(self.nodes) >= 2):
            p = [self.node_pool[n] for n in self.nodes[pivot_node:end_node:step]]
            return math.atan2(p[1].lon - p[0].lon, p[1].lat - p[0].lat)
        else:
            return None

class HwySeg(Seg):
    def __init__(self, el, node_pool):
        super().__init__(el, node_pool)

        self.links = []

    def update_links(self, hwyIndex, linkIndex):
        super().update_links(hwyIndex, linkIndex)

        # Additionally, connect links
        self.links = []
        for l in linkIndex.lookup_all(self.nodes):
            link = linkIndex.get(l[1])
            # On borders:
            #  - exits get appended to next segment
            #  - entrances get appended to previous segment
            if link.start != self.end and link.end != self.start:
                self.links.append(l)

    # Get the angle of a link relative to this segment
    def get_rel_ang(self, link):
        link_type = self.get_link_type(link)
        if(link_type is None):
            return None

        rev = (link_type == 'entrance')
        center_id = link.end if rev else link.start
        start_node = self.nodes.index(center_id)
        diff = link.get_ang(rev) - self.get_ang(rev, start_node)

        if(abs(diff) == math.radians(180)):
            raise ValueError("Exit 180 degrees from road!")

        if(abs(diff) > math.radians(180)):
            diff -= math.copysign(math.radians(360),diff)

        return diff

    # Link type depends inherently on what trunk it's with respect to
    # One highway's exit can be another's entrance
    def get_link_type(self, link):
        if((link.start in self.nodes) and (link.start != self.end)):
            return 'exit'
        elif((link.end in self.nodes) and (link.end != self.start)):
            return 'entrance'
        else:
            print(link.start, link.end)
            print(self.nodes)
            return None

    # Determine left-hand vs right-hand exits
    # Based on angle of exit wrt hwy
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

class LinkSeg(Seg):
    def __init__(self, el, node_pool):
        super().__init__(el, node_pool)

        self.dest_links = {}

    def get_dest(self):
        if self.dest:
            return self.dest
        if self.dest_links.values():
            return '/'.join([l.get_tag('name', 'ref') for l in self.dest_links.values() if l.get_tag('name', 'ref')])

        return '???'

    def describe_link(self, trunk):
        link_type = trunk.get_link_type(self)
        dest = self.get_dest()
        if(link_type == 'exit'):
            side = trunk.get_side(self)
            return '{}: {}'.format(self.get_number(), dest)
        else:
            return dest

    def get_number(self):
        return self.node_pool[self.start].name

class Hwy:
    def __init__(self, name, parent):
        self.name = name

        self.starts = []
        self.ends = []
        self.parent = parent

    def add_seg(self, seg):
        if(seg.is_start()):
            self.starts.append(seg)
        elif(seg.is_end()):
            self.ends.append(seg)

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
    def __init__(self, segs):
        self.hwys = {}
        self.seg_pool = segs

        for s in self.seg_pool.segs.values():
            self.add_seg(s)

    def add_hwy(self, name):
        self.hwys[name] = Hwy(name, self)

    def add_seg(self, seg):
        for name in seg.get_hwys():
            if name not in self.hwys:
                self.add_hwy(name)
            self.hwys[name].add_seg(seg)

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

    def lookup_seg(self, node_id, idx, partition=None):
        res_id = self.lookup(node_id, idx, partition)
        if res_id:
            return self.get(res_id)
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
        seen_ids = []
        while(link_id):
            if link_id in seen_ids:
                print("I seem to have found a loop...", file=sys.stderr)
                print(seen_ids, file=sys.stderr)
                break
            seen_ids.append(link_id)

            cur_link = self.get(link_id)
            cur_node = getattr(cur_link, relattr)
            print("Looking for {} of segment {} at {}...".format(direction, link_id, cur_node))
            link_id = self.lookup(getattr(cur_link, direction), relattr)

        return cur_link
