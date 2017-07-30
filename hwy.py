import math
import sys
from collections import defaultdict

class OsmElm:
    def __init__(self, el):
        self.el = el

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

class Node(OsmElm):
    def __init__(self, xmlobj):
        super().__init__(xmlobj)

        self.id = int(xmlobj.get('id'))
        self.lat = float(xmlobj.get('lat'))
        self.lon = float(xmlobj.get('lon'))
        try:
            nodetype = self.get_tag('highway')
            if(nodetype == 'motorway_junction'):
                self.name = self.get_tag('ref')
            else:
                self.name = None
        except AttributeError:
            self.name = None

class Network:
    def __init__(self, osmTree):
        self.xml = osmTree
        self.nodes = {}
        self.hwys = {}
        self.link_segs = SegIndex()
        self.hwy_segs = SegIndex('get_hwys')

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
                self.hwy_segs.add(HwySeg(way, self))
            elif(seg_type == 'motorway_link'):
                self.link_segs.add(LinkSeg(way, self))

    def parse_aux_ways(self, osmTree):
        for way in osmTree.iter('way'):
            newseg = Seg(way, self)
            for n_id in newseg.nodes:
                for match_id in self.link_segs.lookup(n_id, 'start'):
                    if(match_id and match_id != newseg.id):
                        for end_link in self.link_segs.lookup_last(match_id, 'end'):
                            print("Matched entrance link {} to segment {} from {} via node {}".format(newseg.id, end_link.id, match_id, n_id), file=sys.stderr)
                            end_link.aux_links[newseg.id] = newseg

    def link_ways(self):
        for s in self.hwy_segs.segs.values():
            s.post_process(self.hwy_segs, self.link_segs)

        for s in self.link_segs.segs.values():
            s.post_process(self.hwy_segs, self.link_segs)

    def dump_link_nodes(self, types):
        nodes = set()
        for curseg in self.hwy_segs.segs.values():
            nodes.update(curseg.dump_link_nodes(types))

        return nodes

class Seg(OsmElm):
    lane_keys = ['turn','hov','hgv','bus','motor_vehicle','motorcycle']

    def __init__(self, el, network):
        super().__init__(el)
        self.network = network
        self.node_pool = network.nodes

        self.id = int(self.el.attrib.get('id'))

        self.nodes = [int(sel.attrib.get('ref')) for sel in el.findall('nd')]
        self.start = self.nodes[0]
        self.end = self.nodes[-1]

        self.name = self.get_tag('ref')
        self.type = self.get_tag('highway')

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

    def get_name(self):
        name = self.get_tag('name', 'ref')
        if name:
            return name

        if self.get_tag('highway') == 'service':
            return 'Rest Area'

        return None

    def get_hwys(self):
        if(self.name):
            return self.name.split(';')
        else:
            return [None]

    def is_end(self, hwy = None):
        return (self.prev(hwy) and not self.next(hwy))

    def is_start(self, hwy = None):
        return (self.next(hwy) and not self.prev(hwy))

    def is_link(self):
        return (self.type == 'motorway_link')

    def get_index(self):
        raise NotImplementedError("Abstract method get_index not implemented")

    def next(self, hwy = None):
        if not hwy:
            hwy = self.get_hwys()[0]

        return self.get_index().lookup_segs(self.end, 'start', hwy)

    def prev(self, hwy = None):
        if not hwy:
            hwy = self.get_hwys()[0]

        return self.get_index().lookup_segs(self.start, 'end', hwy)

    def post_process(self, hwyIndex, linkIndex):
        pass

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
    def __init__(self, el, network):
        super().__init__(el, network)

        self.links = []

    def get_index(self):
        return self.network.hwy_segs

    def post_process(self, hwyIndex, linkIndex):
        super().post_process(hwyIndex, linkIndex)

        # Additionally, connect links
        self.links = []
        for l in linkIndex.lookup_all(self.nodes):
            link = l[1]
            # On borders:
            #  - exits get appended to next segment
            #  - entrances get appended to previous segment
            if link.start != self.end and link.end != self.start:
                self.links.append(l)

        # Find connecting highways
#       for l in hwyIndex.lookup_all(self.nodes):
#           link = l[1]
#           # On borders:
#           #  - exits get appended to next segment
#           #  - entrances get appended to previous segment
#           if link.start != self.end and link.end != self.start:
#               self.links.append(l)

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
            print(link.start, link.end, file=sys.stderr)
            print(self.nodes, file=sys.stderr)
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

    def dump_link_nodes(self, types='all'):
        if not isinstance(types, list):
            types = ['entrance', 'exit'] if types == 'all' else [types]

        nodes = set()
        for (t, link) in self.links:
            if(t in types and not isinstance(link, HwySeg)):
                towards = ('start' if t == 'entrance' else 'end')
                lasts = self.network.link_segs.lookup_last(link.id, towards)
                nodes.update([getattr(last, towards) for last in lasts])

        return nodes

    def describe_link(self, trunk):
        return self.get_hwys()[0]

class LinkSeg(Seg):
    def __init__(self, el, node_pool):
        super().__init__(el, node_pool)

        self.dest = None
        self.source = None
        self.aux_links = {}

    def get_index(self):
        return self.network.link_segs

    def get_junction(self, trunk):
        link_type = trunk.get_link_type(self)
        return self.start if (link_type == 'exit') else self.end

    def get_aux(self):
        if self.aux_links.values():
            self.aux = '/'.join(set([l.get_name() for l in self.aux_links.values() if l.get_name()]))
            return self.aux
        else:
            return None

    def get_source(self, trunk):
        if not self.source:
            self.source = self.get_aux()
            if(self.source):
                return self.source

            self.source = '???'

        return self.source

    def get_dest(self, trunk):
        if not self.dest:
            self.dest = self.get_tag('destination:ref:to', 'destination:ref', 'destination')
            if(self.dest):
                return self.dest

            self.dest = self.node_pool[self.get_junction(trunk)].get_tag('exit_to', 'exit_to:left', 'exit_to:right')
            if(self.dest):
                return self.dest

            self.dest = self.get_aux()
            if(self.dest):
                return self.dest

            self.dest = '???'

        return self.dest

    def describe_link(self, trunk):
        link_type = trunk.get_link_type(self)
        desc = self.get_dest(trunk) if link_type == 'exit' else self.get_source(trunk)
        if(link_type == 'exit'):
            return '{}: {}'.format(self.get_number(), desc)
        else:
            return desc

    def get_number(self):
        return self.node_pool[self.start].name

class Hwy:
    def __init__(self, name, parent):
        self.name = name

        self.starts = []
        self.ends = []
        self.parent = parent

    def add_seg(self, seg):
        if(seg.is_start(self.name)):
            self.starts.append(seg)
        elif(seg.is_end(self.name)):
            self.ends.append(seg)

    def lookup(self, node_id, idx_key):
        idx = self.parent.seg_pool
        segs = idx.lookup_segs(node_id, idx_key, self.name)

        if not len(segs):
            return None

        # Merge segments as necessary
        trunk = max(segs, key=lambda s: s.lanes)
        for branch in segs:
            if branch == trunk:
                continue
            trunk = self.merge_lanes(trunk, branch, idx_key)

        return trunk

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

    def next(self, relseg):
        return self.lookup(relseg.end, 'start')

    def prev(self, relseg):
        return self.lookup(relseg.start, 'end')

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

class SegIndex:
    no_seg = '_all_'

    def __init__(self, partition_by = None):
        self.segs = {}
        self.indexes = {
            'start': defaultdict(lambda: defaultdict(set)),
            'end': defaultdict(lambda: defaultdict(set)),
        }
        self.partition_by = partition_by

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
        cur_idx[getattr(seg, idx_key)].add(seg.id)

    def lookup(self, node_id, idx, partition=None):
        if not partition:
            partition = self.no_seg

        node_id = int(node_id)
        lookup = self.indexes[idx][partition]

        return lookup[node_id]

    def lookup_segs(self, node_id, idx, partition=None):
        id_list = self.lookup(node_id, idx, partition)
        return [self.get(i) for i in id_list]

    def lookup_all(self, node_ids, partition = None):
        matches = []
        for node_id in node_ids:
            for idx_type in self.indexes.keys():
                link_type = 'exit' if idx_type == 'start' else 'entrance'

                seg_ids = self.lookup(node_id, idx_type, partition)
                matches += [
                    (link_type, self.get(s))
                    for s in seg_ids
                ]

        return matches

    def lookup_last(self, link_id, towards, seen_ids = []):
        outlinks = set()

        if link_id in seen_ids:
            print("I seem to have found a loop...", file=sys.stderr)
            print(seen_ids, file=sys.stderr)
            return []
        seen_ids.append(link_id)

        cur_link = self.get(link_id)
        next_node = getattr(cur_link, towards)
        print("Looking for {} of segment {} at {}...".format(towards, link_id, next_node), file=sys.stderr)
        next_links = self.lookup(next_node, 'end' if towards == 'start' else 'start')

        if len(next_links):
            for l in next_links:
                outlinks.update(self.lookup_last(l, towards, seen_ids))
        else:
            return [cur_link]

        return outlinks
