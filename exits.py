import xml.etree.ElementTree as ET
from hwy import Node, HwySeg, Hwy, HwySet
import render

tree = ET.parse('motorway.osm')
root = tree.getroot()

# Get ways
nodes_to_hwy = {}
hwys = {}
hwy_segs = {}
hwy_names = set()
hwy_start = {}
hwy_end = {}
links = {}

print("Getting nodes...")
nodes = {}
for n in root.iter('node'):
    curnode = Node(n)
    nodes[curnode.id] = curnode

print("Getting ways...")
for way in root.iter('way'):
    seg = HwySeg(way, nodes)

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
hwys = HwySet(hwy_segs)
for name in hwy_names:
    hwys.add_hwy(name, hwy_start[name], hwy_end[name])

for (id, seg) in hwy_segs.items():
    hwys.add_seg(seg)

for (id, link) in links.items():
    hwys.add_link(link)

dwg = render.Drawing(10)
for start in hwys.get_hwy('I 5').starts:
    curseg = start
    curlanes = start.lanes
    while curseg.next:
        if(curlanes != curseg.lanes or len(curseg.exits) or len(curseg.entrances)):
            row = dwg.add_row(0)
            for n in range(curlanes):
                row.add_element(render.Lane())
            lanes = 'H'*curlanes
            if(len(curseg.exits)):
                lanes += '-> ' + ';'.join([s.describe_link(curseg) for s in curseg.exits])
                row.add_element(render.Exit())
            if(len(curseg.entrances)):
                lanes += '<-' + ';'.join([s.describe_link(curseg) for s in curseg.exits])
                row.add_element(render.Entrance())
            print(lanes)
            curlanes = curseg.lanes
        curseg = curseg.next
    print('H'*curlanes)
    print("---")
    dwg.add_row(0)

dwg.render()
dwg.save()
