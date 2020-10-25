# -*- coding: utf-8 -*-

import sys
import shlex
import re
from pathlib import Path

trans_p = re.compile('\t([\-0-9]+)\s+([\-0-9]+)\s+([\-0-9]+)\s+([\-0-9]+)')
t0  = '	1    0    0    -1'
t0f  = '	1    0    0    1'
t180 = '	-1   0    0    1'
t180f = '	-1   0    0    -1' # this is flipped horizontally
tM90 = '	0    1    1    0'
t90  = '	0    -1   -1   0'
tunk  = '	0    1   -1   0'
orientations = {
    str(trans_p.match(t0).groups()): 0,
    str(trans_p.match(t0f).groups()): 0, # TWS added to handle flipped, but no rotation
    str(trans_p.match(t180).groups()): 180,
    str(trans_p.match(t180f).groups()): 180,
    str(trans_p.match(tM90).groups()): -90,
    str(trans_p.match(t90).groups()): 90,
    str(trans_p.match(tunk).groups()) : 0
}

def ensure_quoted(s):
    """
    Returns a quoted version of string 's' if that's not already the case
    """
    rx = r"^\"(.+)\"$"

    if re.match(rx, s) is not None:
        return s
    else:
        return "\"{}\"".format(s)


class Description(object):
    """
    A class to parse description information of Schematic Files Format of the KiCad
    TODO: Need to be done, currently just stores the raw data read from file
    """
    def __init__(self, data):
        self.raw_data = data


class Component(object):
    """
    A class to parse components of Schematic Files Format of the KiCad
    """
    _L_KEYS = ['name', 'ref']
    _U_KEYS = ['unit', 'convert', 'time_stamp']
    _P_KEYS = ['posx', 'posy']
    _AR_KEYS = ['path', 'ref', 'part']
    _F_KEYS = ['id', 'ref', 'orient', 'posx', 'posy', 'size', 'attributs',
               'hjust', 'props', 'name']

    _KEYS = {'L': _L_KEYS, 'U': _U_KEYS, 'P': _P_KEYS,
             'AR': _AR_KEYS, 'F': _F_KEYS}

    def __init__(self, data):
        self.labels = {}
        self.unit = {}
        self.position = {}
        self.references = []
        self.fields = []
        self.old_stuff = []

        for line in data:
            if line[0] == '\t':
                self.old_stuff.append(line)
                continue

            line = line.replace('\n', '')
            s = shlex.shlex(line)
            s.whitespace_split = True
            s.commenters = ''
            s.quotes = '"'
            line = list(s)

            # select the keys list and default values array
            if line[0] in self._KEYS:
                key_list = self._KEYS[line[0]]
                values = line[1:] + ['']*(len(key_list) - len(line[1:]))

            if line[0] == 'L':
                self.labels = dict(zip(key_list, values))
            elif line[0] == 'U':
                self.unit = dict(zip(key_list, values))
            elif line[0] == 'P':
                self.position = dict(zip(key_list, values))
            elif line[0] == 'AR':
                self.references.append(dict(zip(key_list, values)))
            elif line[0] == 'F':
                self.fields.append(dict(zip(key_list, values)))
        trans = trans_p.match(self.old_stuff[1])
        self.orient = orientations[str(trans.groups())]

    # TODO: enhancements
    # * 'value' could be used instead of 'ref'
    def addField(self, *, ref, name, **field_data):
        field = {'id': None, 'ref': None, 'orient': 'H', 'posx': '0',
                 'posy': '0', 'size': '50', 'attributs': '0001',
                 'hjust': 'C', 'props': 'CNN', 'name': '~'}

        # 'ref' and 'name' must be quoted
        ref = ensure_quoted(ref)
        name = ensure_quoted(name)

        # ignore invalid items in field_data
        field_data = {key: val for (key, val) in field_data.items()
                      if key in self._F_KEYS}

        # merge dictionaries and set the id value
        field.update(field_data, ref=ref, name=name)
        field['id'] = str(len(self.fields))

        self.fields.append(field)
        return field


class Sheet(object):
    """
    A class to parse sheets of Schematic Files Format of the KiCad
    """
    _S_KEYS = ['topLeftPosx', 'topLeftPosy', 'botRightPosx', 'botRightPosy']
    _U_KEYS = ['uniqID']
    _F_KEYS = ['id', 'value', 'IOState', 'side', 'posx', 'posy', 'size']

    _KEYS = {'S': _S_KEYS, 'U': _U_KEYS, 'F': _F_KEYS}

    def __init__(self, data,parent_filename):
        self.shape = {}
        self.unit = {}
        self.fields = []
        for line in data:
            line = line.replace('\n', '')
            s = shlex.shlex(line)
            s.whitespace_split = True
            s.commenters = ''
            s.quotes = '"'
            line = list(s)
            # select the keys list and default values array
            if line[0] in self._KEYS:
                key_list = self._KEYS[line[0]]
                values = line[1:] + ['']*(len(key_list) - len(line[1:]))
            if line[0] == 'S':
                self.shape = dict(zip(key_list, values))
            elif line[0] == 'U':
                self.unit = dict(zip(key_list, values))
            elif line[0][0] == 'F':
                key_list = self._F_KEYS
                values = line + ['' for n in range(len(key_list) - len(line))]
                to_append = dict(zip(key_list, values))
                if(to_append["id"]=="F1"):
                    self.filename = to_append['value'][1:-1]
                self.fields.append(to_append)
        
        p = Path(parent_filename)
        self.path = p.parent.joinpath(self.filename)
        if(self.path.exists):
            self.sch = Schematic(self.path)


class Bitmap(object):
    """
    A class to parse bitmaps of Schematic Files Format of the KiCad
    TODO: Need to be done, currently just stores the raw data read from file
    """
    def __init__(self, data):
        self.raw_data = data


class Schematic(object):
    """
    A class to parse Schematic Files Format of the KiCad
    """
    def __init__(self, filename):
        f = open(filename)
        self.filename = filename
        self.header = f.readline()
        self.libs = []
        self.eelayer = None
        self.description = None
        self.components = []
        self.sheets = []
        self.bitmaps = []
        self.texts = []
        self.wires = []
        self.entries = []
        self.conns = []
        self.noconns = []

        if 'EESchema Schematic File' not in self.header:
            self.header = None
            sys.stderr.write('The file is not a KiCad Schematic File\n')
            return

        building_block = False

        while True:
            line = f.readline()
            if not line:
                break

            if line.startswith('LIBS:'):
                self.libs.append(line)

            elif line.startswith('EELAYER END'):
                pass
            elif line.startswith('EELAYER'):
                self.eelayer = line

            elif not building_block:
                if line.startswith('$'):
                    building_block = True
                    block_data = []
                    block_data.append(line)
                elif line.startswith('Text'):
                    data = {'desc': line, 'data': f.readline()}
                    self.texts.append(data)
                elif line.startswith('Wire'):
                    data = {'desc': line, 'data': f.readline()}
                    self.wires.append(data)
                elif line.startswith('Entry'):
                    data = {'desc': line, 'data': f.readline()}
                    self.entries.append(data)
                elif line.startswith('Connection'):
                    data = {'desc': line}
                    self.conns.append(data)
                elif line.startswith('NoConn'):
                    data = {'desc': line}
                    self.noconns.append(data)

            elif building_block:
                block_data.append(line)
                if line.startswith('$End'):
                    building_block = False

                    if line.startswith('$EndDescr'):
                        self.description = Description(block_data)
                    if line.startswith('$EndComp'):
                        self.components.append(Component(block_data))
                    if line.startswith('$EndSheet'):
                        self.sheets.append(Sheet(block_data,filename))
                    if line.startswith('$EndBitmap'):
                        self.bitmaps.append(Bitmap(block_data))

def get_all_components(sheets):
    all_components = []
    for sheet in sheets:
        if sheet.sch:
            all_components.extend(sheet.sch.components)

            if sheet.sch.sheets:
                all_components.extend(get_all_components(sheet.sch.sheets))
    return all_components


def get_locations(filename):
    top = Schematic(filename)
    all_comps = top.components
    all_comps.extend(get_all_components(top.sheets))

    locs = {}
    for comp in all_comps:
        item = { "pos":comp.position , "comp":comp , "degree":comp.orient}
        locs[comp.labels["ref"]] = item
    return locs
