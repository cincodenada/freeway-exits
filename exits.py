import xml.etree.ElementTree as ET
from hwy import Node, HwySeg, Hwy, HwySet, SegIndex
import render

tree = ET.parse('motorway.osm')
root = tree.getroot()

# Get ways
hwys = {}
hwy_names = set()

hwy_segs = SegIndex('name', dedup=True)
links = SegIndex()

print("Getting nodes...")
nodes = {}
for n in root.iter('node'):
    curnode = Node(n)
    nodes[curnode.id] = curnode

print("Getting ways...")
for way in root.iter('way'):
    try:
        if(way.find("./tag[@k='oneway']").get('v') != 'yes'):
            continue
    except AttributeError:
        continue

    seg = HwySeg(way, nodes)

    if(seg.type == 'motorway'):
        hwy_segs.add(seg)
        hwy_names.add(seg.name)
    elif(seg.type == 'motorway_link'):
        links.add(seg)

print("Analyzing...")
hwys = HwySet(hwy_segs, links)
for name in hwy_names:
    hwys.add_hwy(name)

for seg in hwy_segs.segs.values():
    hwys.add_seg(seg)

dwg = render.Diagram(20)
for start in hwys.get_hwy('I 5').starts:
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
                        row = dwg.add_row()
                        for n in range(lastlanes):
                            row.add_lane(render.Lane())

                    row = dwg.add_row()
                    for n in range(curlanes):
                        row.add_lane(render.Lane())

                    if(type == 'exit'):
                        row.add_link(render.Exit(side))
                        last_link_diff = -1
                    else:
                        row.add_link(render.Entrance(side))
                        last_link_diff = 1
                    row.add_link(render.Label(side, type, link.describe_link(curseg)))

                    # Update lastlanes for entrance rendering
                    lastlanes = curlanes
            else:
                # If we had links last time,
                # Add a lane to make room for the expansion
                if(lastlinks > 0):
                    row = dwg.add_row()
                    for n in range(lastlanes):
                        row.add_lane(render.Lane())

                row = dwg.add_row()
                for n in range(curlanes):
                    row.add_lane(render.Lane())

        lastlanes = curlanes
        lastlinks = len(curseg.links)
        extra_lanes -= curseg.remove_lanes
        curseg = curseg.next
    dwg.add_row(0)

dwg.render('text')
dwg.render()
dwg.save()
