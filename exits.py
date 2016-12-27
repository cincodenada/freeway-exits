import xml.etree.ElementTree as ET
from hwy import Node, HwySeg, Hwy, HwySet

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

print(links[452336723].get_ang(True))
print(hwy_segs[4748960].get_ang(False))
print(links[436165683].get_ang(False))

# L
print(hwy_segs[452336740].get_side(links[452336723]))
# R
print(hwy_segs[4748960].get_side(links[436165683]))
# R
print(hwy_segs[428232211].get_side(links[96260970]))
# L
print(hwy_segs[14017470].get_side(links[85106512]))
# Breaks, not correct seg
print(hwy_segs[5130429].get_side(links[85106512]))

hwys = HwySet(hwy_segs)
for name in hwy_names:
    hwys.add_hwy(name, hwy_start[name], hwy_end[name])

for (id, seg) in hwy_segs.items():
    hwys.add_seg(seg)

for (id, link) in links.items():
    hwys.add_link(link)

for start in hwys.get_hwy('I 5').starts:
    curseg = start
    curlanes = start.lanes
    while curseg.next:
        if(curlanes != curseg.lanes or len(curseg.exits) or len(curseg.entrances)):
            lanes = 'H'*curlanes
            if(len(curseg.exits)):
                lanes += '-> ' + ';'.join([s.describe_link(curseg) for s in curseg.exits])
            if(len(curseg.entrances)):
                lanes += '<-' + ';'.join([s.describe_link(curseg) for s in curseg.exits])
            print(lanes)
            curlanes = curseg.lanes
        curseg = curseg.next
    print('H'*curlanes)
    print("---")
