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
    lastlanes = start.lanes
    prevlanes = start.lanes
    base_pos = 0
    while curseg.next:
        if(lastlanes != curseg.lanes or curseg.exit or curseg.entrance):
            left_exit = curseg.exit and curseg.get_side(curseg.exit) == 'L'

            if(left_exit):
                print(curseg.exit)
                print(curseg.exit.describe_link(curseg))
                print('{}->{}'.format(lastlanes, curseg.lanes))

            if(left_exit and prevlanes > lastlanes):
                base_pos += 1

            text_adj = -2 if left_exit else 0
            row = dwg.add_row(base_pos + text_adj)
            for n in range(lastlanes):
                row.add_element(render.Lane())
            lanes = 'H'*lastlanes
            if(curseg.exit):
                is_left = (curseg.get_side(curseg.exit) == 'L')
                row.add_element(render.Exit(), is_left)
                row.add_element(render.Label(curseg.exit.describe_link(curseg)), is_left)
                lanes += '-> ' + curseg.exit.describe_link(curseg)
            if(curseg.entrance):
                is_left = (curseg.get_side(curseg.entrance) == 'L')
                row.add_element(render.Entrance(), is_left)
                row.add_element(render.Label(curseg.entrance.describe_link(curseg)), is_left)
                lanes += '<-' + curseg.entrance.describe_link(curseg)
            print(lanes)
            prevlanes = lastlanes
            lastlanes = curseg.lanes
        curseg = curseg.next
    print('H'*lastlanes)
    print("---")
    dwg.add_row(0)

dwg.render()
dwg.save()
