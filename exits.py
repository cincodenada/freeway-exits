import xml.etree.ElementTree as ET
from hwy import Node, HwySeg, Hwy, HwySet, SegIndex
import render

tree = ET.parse('motorway.osm')
root = tree.getroot()

# Get ways
hwys = {}
hwy_names = set()

hwy_segs = SegIndex('name')
links = SegIndex()

print("Getting nodes...")
nodes = {}
for n in root.iter('node'):
    curnode = Node(n)
    nodes[curnode.id] = curnode

print("Getting ways...")
for way in root.iter('way'):
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
    base_pos = 0
    while curseg.next:
        if(lastlanes != curseg.lanes or len(curseg.links)):
            if(len(curseg.links)):
                for (type, link_id) in curseg.links:
                    link = links.get(link_id)
                    is_left = (curseg.get_side(link) == 'L')

                    # If we lost a lane and there's a left exit,
                    # shift the lanes over 1 to make the leftmost lane an exit
                    if(is_left and lastlanes > curseg.lanes):
                        base_pos += 1
                    text_adj = -2 if is_left else 0
                    row = dwg.add_row(base_pos + text_adj)
                    for n in range(curseg.lanes):
                        row.add_element(render.Lane())

                    if(type == 'exit'):
                        row.add_element(render.Exit(), is_left)
                    else:
                        row.add_element(render.Entrance(), is_left)
                    row.add_element(render.Label(link.describe_link(curseg)), is_left)

                    # Update lastlanes for entrance rendering
                    lastlanes = curseg.lanes
            else:
                row = dwg.add_row(base_pos)
                for n in range(curseg.lanes):
                    row.add_element(render.Lane())

        lastlanes = curseg.lanes
        curseg = curseg.next
    dwg.add_row(0)

dwg.render('text')
dwg.render()
dwg.save()
