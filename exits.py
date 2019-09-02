#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from hwy import Network
import render
from glob import glob
import sys
import argparse

parser = argparse.ArgumentParser(description = "Build a visualization of highways from OSM data")
parser.add_argument('--svg', help="SVG file to output to")
parser.add_argument('--dump-nodes', action='store_true', help="Dump entrance/exit nodes for links")
parser.add_argument('--dump-type', default='all', help="Which type of nodes to dump", choices=['exit','entrance','all'])
parser.add_argument('--osm-file', default='motorway.osm', help="OSM file to ingest")
parser.add_argument('--aux-file', default='link_nodes', help="Prefix to use for aux node files")
parser.add_argument('--highway', default='I 5', help="OSM ref of highway to render")
args = parser.parse_args()

tree = ET.parse(args.osm_file)
net = Network(tree.getroot())

if(args.dump_nodes):
    for n in net.dump_link_nodes(args.dump_type):
        print(n)
    sys.exit(0)

print("Getting entrance ways...", file=sys.stderr)
for efile in glob(args.aux_file + "_*.osm"):
    print("Parsing {}...".format(efile), file=sys.stderr)
    tree = ET.parse(efile)
    net.parse_aux_ways(tree.getroot())

dwg = render.Diagram(20)
hwy_name = args.highway
hwy = net.hwys.get_hwy(hwy_name)
for start in hwy.starts:
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
        print("Lanes/links:", lastlanes, curlanes, len(curseg.links), file=sys.stderr)
        if(lastlanes != curlanes or len(curseg.links)):
            lane_diff = (curlanes - lastlanes)

            if(len(curseg.links)):
                for (idx, linkdata) in enumerate(curseg.links):
                    (type, link) = linkdata
                    side = curseg.get_side(link)

                    # Exits apply to this row
                    if(type == 'exit'):
                        link_sub = 1
                    else:
                        link_sub = 0

                    print(link.describe_link(curseg), file=sys.stderr)
                    print("Diff:", lane_diff, -link_sub, link_add, file=sys.stderr)
                    # Add an extra row if we have lane changes
                    # that aren't accounted for by exits/entrances
                    if(idx == 0):
                        if(lane_diff < 0 and -lane_diff > link_sub):
                            print("Adding buffer row...", file=sys.stderr)
                            row = curhwy.add_row()
                            for n in range(curlanes):
                                row.add_lane(render.Lane())
                        elif(lane_diff > 0 and lane_diff > link_add):
                            print("Adding buffer row...", file=sys.stderr)
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
                    print("Adding buffer row...", file=sys.stderr)
                    row = curhwy.add_row()
                    for n in range(curlanes):
                        row.add_lane(render.Lane())
                elif(lane_diff > 0 and lane_diff > link_add):
                    print("Adding buffer row...", file=sys.stderr)
                    row = curhwy.add_row()
                    for n in range(lastlanes):
                        row.add_lane(render.Lane())

                row = curhwy.add_row()
                for n in range(curlanes):
                    row.add_lane(render.Lane())

        lastlanes = curlanes
        lastlinks = len(curseg.links)
        extra_lanes -= curseg.remove_lanes
        curseg = hwy.next(curseg)

dwg.render('text')
if(args.svg):
    print("Rendering SVG...", file=sys.stderr)
    dwg.render()
    print("Writing...", file=sys.stderr)
    dwg.save(args.svg)
