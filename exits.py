import xml.etree.ElementTree as ET

tree = ET.parse('motorway.osm')
root = tree.getroot()

class OsmEl(ET.Element):
    def get_tag(self, k):
        subel = self.find("./tag[@k='{}']".format(k))
        if(subel):
            return subel.attrib.get('v')
        else:
            return None
#   if(hasattr(name, 'get')):
#       print(name.get('v'))
#   elif(hasattr(name, 'attrib')):
#       print(name.attrib.get('v'))

class HwySeg:
    def __init__(self, el):
        self.el = OsmEl(el)

        self.id = self.el.attrib.get('id')

        self.nodes = [int(sel.attrib.get('ref')) for sel in el.findall('nd')]
        self.start = self.nodes[0]
        self.end = self.nodes[-1]

        self.name = self.el.get_tag('ref')
        self.type = self.el.get_tag('highway')

        self.lanes = self.el.get_tag('lanes')
        self.lanedata = {}
        for lanetype in self.el.findall("./tag[substring-after(@k, ':')='lanes']"):
            k = lanetype.attrib('k').split(':')
            self.lanedata[k[-1]] = lanetype.attrib('v').split('|')

# Get ways
hwy_ways = {}
links_start = {}
links_end = {}
for way in root.iter('way'):
    hwy = HwySeg(way)

    print(hwy.id)

    if(hwy.type == 'motorway'):
        hwy_ways[hwy.start] = hwy
    elif(hwy.type == 'motorway_link'):
        links_start[hwy.start] = hwy
        links_end[hwy.end] = hwy
