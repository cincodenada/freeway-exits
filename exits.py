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

dwg = render.Diagram(20)
for start in hwys.get_hwy('I 5').starts:
    curseg = start
    lastlanes = start.lanes
    base_pos = 0
    while curseg.next:
        if(lastlanes != curseg.lanes or curseg.exit or curseg.entrance):
            lanes = 'H'*curseg.lanes
            if(curseg.exit):
                is_left = (curseg.get_side(curseg.exit) == 'L')

                # If we lost a lane and there's a left exit,
                # shift the lanes over 1 to make the leftmost lane an exit
                if(is_left and lastlanes > curseg.lanes):
                    base_pos += 1
                text_adj = -2 if is_left else 0
                row = dwg.add_row(base_pos + text_adj)
                for n in range(curseg.lanes):
                    row.add_element(render.Lane())

                row.add_element(render.Exit(), is_left)
                row.add_element(render.Label(curseg.exit.describe_link(curseg)), is_left)
                lanes += '-> ' + curseg.exit.describe_link(curseg)

                # Update lastlanes for entrance rendering
                lastlanes = curseg.lanes

            if(curseg.entrance):
                is_left = (curseg.get_side(curseg.entrance) == 'L')

                if(is_left and lastlanes < curseg.lanes):
                    base_pos -= 1
                text_adj = -2 if is_left else 0
                row = dwg.add_row(base_pos + text_adj)
                for n in range(curseg.lanes):
                    row.add_element(render.Lane())

                row.add_element(render.Entrance(), is_left)
                row.add_element(render.Label(curseg.entrance.describe_link(curseg)), is_left)
                lanes += '<-' + curseg.entrance.describe_link(curseg)
            print(lanes)
        lastlanes = curseg.lanes
        curseg = curseg.next
    print('H'*lastlanes)
    print("---")
    dwg.add_row(0)

dwg.render('text')
dwg.render()
dwg.save()
