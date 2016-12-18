import xml.etree.ElementTree as ET

tree = ET.parse('motorway.osm')
root = tree.getroot()

# Get ways
for way in root.iter('way'):
    nodes = way.findall("./nd")
    name = way.find("./tag[@k='ref']")
    if(hasattr(name, 'get')):
        print(name.get('v'))
    elif(hasattr(name, 'attrib')):
        print(name.attrib.get('v'))
    print(way.attrib.get('id'))
    hwy = way.find("./tag[@k='highway']").attrib.get('v')
    print(hwy)
