import xml.etree.ElementTree as ET
from hwy import Network
import render
from glob import glob
import sys
import argparse

parser = argparse.ArgumentParser(description = "Build a visualization of highways from OSM data")
parser.add_argument('--svg', help="SVG file to output to")
args = parser.parse_args()

tree = ET.parse('motorway.osm')
net = Network(tree.getroot())


print("Getting entrance ways...", file=sys.stderr)
for efile in glob("entrance_*.osm"):
    print("Parsing {}...".format(efile))
    tree = ET.parse(efile)
    net.parse_aux_ways(tree.getroot())

dwg = render.Diagram(20)
for start in net.hwys.get_hwy('I 5').starts:
    curhwy = dwg.add_hwy()

    curseg = start
    lastlanes = start.lanes
    lastlinks = len(start.links)
    link_add = 0
    link_sub = 0
    extra_lanes = 0
    base_pos = 0
    while curseg:
        extra_lanes += curseg.add_lanes
        curlanes = curseg.lanes + extra_lanes
        print("Lanes/links:", lastlanes, curlanes, len(curseg.links))
        if(lastlanes != curlanes or len(curseg.links)):
            lane_diff = (curlanes - lastlanes)

            if(len(curseg.links)):
                for (idx, linkdata) in enumerate(curseg.links):
                    (type, link_id) = linkdata
                    link = net.links.get(link_id)
                    side = curseg.get_side(link)

                    # Exits apply to this row
                    if(type == 'exit'):
                        link_sub = 1
                    else:
                        link_sub = 0

                    print(link.describe_link(curseg))
                    print("Diff:", lane_diff, -link_sub, link_add)
                    # Add an extra row if we have lane changes
                    # that aren't accounted for by exits/entrances
                    if(idx == 0):
                        if(lane_diff < 0 and -lane_diff > link_sub):
                            print("Adding buffer row...")
                            row = curhwy.add_row()
                            for n in range(curlanes):
                                row.add_lane(render.Lane())
                        elif(lane_diff > 0 and lane_diff > link_add):
                            print("Adding buffer row...")
                            row = curhwy.add_row()
                            for n in range(lastlanes):
                                row.add_lane(render.Lane())


                    row = curhwy.add_row()
                    for n in range(curlanes):
                        row.add_lane(render.Lane())

                    if(type == 'exit'):
                        row.add_link(render.Exit(side, link.get_number()))
                    else:
                        row.add_link(render.Entrance(side, link.get_number()))
                    row.add_link(render.Label(side, type, link.describe_link(curseg)))

                    # Entrances apply to next row
                    if(type == 'entrance'):
                        link_add = 1
                    else:
                        link_add = 0

                    # Update lastlanes for entrance rendering
                    lastlanes = curlanes
            else:
                if(lane_diff < 0 and -lane_diff > link_sub):
                    print("Adding buffer row...")
                    row = curhwy.add_row()
                    for n in range(curlanes):
                        row.add_lane(render.Lane())
                elif(lane_diff > 0 and lane_diff > link_add):
                    print("Adding buffer row...")
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
if(args.svg):
    print("Rendering SVG...")
    dwg.render()
    print("Writing...")
    dwg.save(args.svg)
