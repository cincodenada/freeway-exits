import xml.etree.ElementTree as ET

tree = ET.parse('motorway.osm')
root = tree.getroot()

class HwySeg:
    lane_keys = ['turn','hov','bus']
    def __init__(self, el):
        self.el = el

        self.id = self.el.attrib.get('id')

        self.nodes = [int(sel.attrib.get('ref')) for sel in el.findall('nd')]
        self.start = self.nodes[0]
        self.end = self.nodes[-1]

        self.name = self.get_tag('ref')
        self.type = self.get_tag('highway')

        self.lanes = self.get_tag('lanes')
        self.lanedata = {}
        for key in self.lane_keys:
            lanedata = self.get_tag(key + ':lanes')
            self.lanedata[key] = lanedata.split('|') if lanedata else None

    def get_tag(self, k):
        tagel = self.el.find("./tag[@k='{}']".format(k))
        # I'm not sure why this is necessary?
        # Maybe it's not?
        if(hasattr(tagel, 'get')):
            return tagel.get('v')
        elif(hasattr(tagel, 'attrib')):
            return tagel.attrib.get('v')
        else:
            return None

# Get ways
hwy_ways = {}
links_start = {}
links_end = {}
for way in root.iter('way'):
    hwy = HwySeg(way)

    print(hwy.id)
    print(hwy.type)

    if(hwy.type == 'motorway'):
        hwy_ways[hwy.start] = hwy
    elif(hwy.type == 'motorway_link'):
        links_start[hwy.start] = hwy
        links_end[hwy.end] = hwy
