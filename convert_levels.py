from Converter import resource
from Converter.converter import Converter
import Converter.pict.reader as pReader
from lxml import etree
import argparse
import sys


def try_read(file):
    f = open(file, 'rb')
    data = f.read()

    if len(data) == 0:
        print("Couldn't read resource fork directly")

        f = open(file + '/..namedfork/rsrc', 'rb')
        data = f.read()

        if len(data) == 0:
            print("Couldn't read resource fork from /..namedfork/")
            return False
        else:
            return data
    else:
        return data


def get_resources(file):
    data = try_read(file)
    if data is False:
        print("No data to read")
        sys.exit(1)
    reader = resource.Reader()
    resources = reader.parse(data)

    return resources


def convert_map(pict):
    for pict in pict.values():
        ops = pReader.parse(pict['data'])
        conv = Converter()
        mapxml = conv.convert(ops)
        filename = pict['name'].decode('macintosh') + '.xml'
        xmlstring = etree.tostring(mapxml, pretty_print=True).decode('macintosh')
        f = open(filename, 'w')
        f.write(xmlstring)
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', metavar='file')

    args = parser.parse_args()

    resources = get_resources(args.file)
    # print resources.keys()
    # print resources['TMPL']
    # print resources['LEDI'][128]['data']
    print(resources.keys())
    convert_map(resources[b'PICT'])
