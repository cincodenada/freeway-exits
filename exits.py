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
        if(lastlanes != curseg.lanes or len(curseg.exits) or len(curseg.entrances)):
            left_exits = len([e for e in curseg.exits if curseg.get_side(e) == 'L'])
            right_exits = len([e for e in curseg.exits if curseg.get_side(e) == 'R'])

            if(left_exits):
                print(curseg.exits)
                print(curseg.exits[0].describe_link(curseg))
                print('{}->{}'.format(lastlanes, curseg.lanes))

            if(left_exits and prevlanes > lastlanes):
                base_pos += 1

            text_adj = -2 if left_exits else 0
            row = dwg.add_row(base_pos + text_adj)
            for n in range(lastlanes):
                row.add_element(render.Lane())
            lanes = 'H'*lastlanes
            if(len(curseg.exits)):
                for link in curseg.exits:
                    is_left = (curseg.get_side(link) == 'L')
                    row.add_element(render.Exit(), is_left)
                    row.add_element(render.Label(link.describe_link(curseg)), is_left)
                lanes += '-> ' + ';'.join([s.describe_link(curseg) for s in curseg.exits])
#           if(len(curseg.entrances)):
#               for link in curseg.entrances:
#                   is_left = (curseg.get_side(link) == 'L')
#                   row.add_element(render.Entrance(), is_left)
#                   row.add_element(render.Label(link.describe_link(curseg)), is_left)
#               lanes += '<-' + ';'.join([s.describe_link(curseg) for s in curseg.entrances])
            print(lanes)
            prevlanes = lastlanes
            lastlanes = curseg.lanes
        curseg = curseg.next
    print('H'*lastlanes)
    print("---")
    dwg.add_row(0)

dwg.render()
dwg.save()
