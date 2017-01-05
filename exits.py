import xml.etree.ElementTree as ET
from hwy import Node, HwySeg, Hwy, HwySet, SegIndex
import render
from glob import glob
import sys

tree = ET.parse('motorway.osm')
root = tree.getroot()

# Get ways
hwys = {}
hwy_names = set()

hwy_segs = SegIndex('get_hwys', dedup=True)
links = SegIndex()
link_entrances = SegIndex()

print("Getting nodes...", file=sys.stderr)
nodes = {}
for n in root.iter('node'):
    curnode = Node(n)
    nodes[curnode.id] = curnode

print("Getting ways...", file=sys.stderr)
for way in root.iter('way'):
    try:
        if(way.find("./tag[@k='oneway']").get('v') != 'yes'):
            continue
    except AttributeError:
        continue

    seg = HwySeg(way, nodes)

    if(seg.type == 'motorway'):
        hwy_segs.add(seg)
        for name in seg.get_hwys():
            hwy_names.add(name)
    elif(seg.type == 'motorway_link'):
        links.add(seg)

print("Getting entrance ways...", file=sys.stderr)
for efile in glob("entrance_*.osm"):
    print("Parsing {}...".format(efile))
    tree = ET.parse(efile)
    root = tree.getroot()

    for way in root.iter('way'):
        curseg = HwySeg(way, None)
        way_id = way.get('id')
        for ndref in way.findall("./nd"):
            n_id = ndref.get('ref')
            seg_id = links.lookup(n_id, 'start')
            if(seg_id and seg_id != way_id):
                #print("Matched entrance link {} to segment {}".format(way_id, seg_id))
                links.get(seg_id).dest = curseg.get_tag('name', 'ref', 'destination', 'destination:ref')

print("Analyzing...", file=sys.stderr)
hwys = HwySet(hwy_segs, links)
for name in hwy_names:
    hwys.add_hwy(name)

for seg in hwy_segs.segs.values():
    hwys.add_seg(seg)

dwg = render.Diagram(20)
for start in hwys.get_hwy('I 5').starts:
    curhwy = dwg.add_hwy()

    curseg = start
    lastlanes = start.lanes
    lastlinks = len(start.links)
    last_link_diff = 0
    extra_lanes = 0
    base_pos = 0
    while curseg.next:
        extra_lanes += curseg.add_lanes
        curlanes = curseg.lanes + extra_lanes
        if(lastlanes != curlanes or len(curseg.links)):
            lane_diff = (curlanes - lastlanes)

            if(len(curseg.links)):
                for (type, link_id) in curseg.links:
                    link = links.get(link_id)
                    side = curseg.get_side(link)

                    # Add an extra row if we have lane changes
                    # that aren't accounted for by exits/entrances
                    if(lane_diff and lane_diff > last_link_diff):
                        row = curhwy.add_row()
                        for n in range(lastlanes):
                            row.add_lane(render.Lane())

                    row = curhwy.add_row()
                    for n in range(curlanes):
                        row.add_lane(render.Lane())

                    if(type == 'exit'):
                        row.add_link(render.Exit(side, link.get_number()))
                        last_link_diff = -1
                    else:
                        row.add_link(render.Entrance(side, link.get_number()))
                        last_link_diff = 1
                    row.add_link(render.Label(side, type, link.describe_link(curseg)))

                    # Update lastlanes for entrance rendering
                    lastlanes = curlanes
            else:
                # If we had links last time,
                # Add a lane to make room for the expansion
                if(lastlinks > 0):
                    row = curhwy.add_row()
                    for n in range(lastlanes):
                        row.add_lane(render.Lane())

                row = curhwy.add_row()
                for n in range(curlanes):
                    row.add_lane(render.Lane())

        lastlanes = curlanes
        lastlinks = len(curseg.links)
        extra_lanes -= curseg.remove_lanes
        curseg = curseg.next

dwg.render('text')
dwg.render()
dwg.save()
