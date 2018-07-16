import svgwrite
from svgwrite import mm
from math import copysign
import symbols as sym
import re

class Diagram:
    text_buffer = 5
    hwy_spacing = 750
    def __init__(self, gridsize):
        self.gs = gridsize
        self.svg = svgwrite.Drawing(debug=True)
        self.hwys = []
        self.cur_horiz = 0
        self.hwy_offset = int(self.hwy_spacing/gridsize)

        self.add_sym("exit_R", sym.Ramp(self.svg, False, False, cap_color='green'))
        self.add_sym("entrance_R", sym.Ramp(self.svg, False, True, cap_color='red'))
        self.add_sym("exit_L", sym.Ramp(self.svg, True, False, cap_color='green'))
        self.add_sym("entrance_L", sym.Ramp(self.svg, True, True, cap_color='red'))

        self.add_sym("exit_cap_R", sym.LaneEnd(self.svg, False, False, cap_color='green'))
        self.add_sym("entrance_cap_R", sym.LaneEnd(self.svg, False, True, cap_color='red'))
        self.add_sym("exit_cap_L", sym.LaneEnd(self.svg, True, False, cap_color='green'))
        self.add_sym("entrance_cap_L", sym.LaneEnd(self.svg, True, True, cap_color='red'))

        self.add_sym("entrance_flip_R", sym.Ramp(self.svg, False, False, cap_color='red'))
        self.add_sym("exit_flip_R", sym.Ramp(self.svg, False, True, cap_color='green'))
        self.add_sym("entrance_flip_L", sym.Ramp(self.svg, True, False, cap_color='red'))
        self.add_sym("exit_flip_L", sym.Ramp(self.svg, True, True, cap_color='green'))

        self.add_sym("entrance_cap_flip_R", sym.LaneEnd(self.svg, False, False, cap_color='red'))
        self.add_sym("exit_cap_flip_R", sym.LaneEnd(self.svg, False, True, cap_color='green'))
        self.add_sym("entrance_cap_flip_L", sym.LaneEnd(self.svg, True, False, cap_color='red'))
        self.add_sym("exit_cap_flip_L", sym.LaneEnd(self.svg, True, True, cap_color='green'))

        self.add_sym("lane_mid", sym.Lane(self.svg))
        self.add_sym("lane_L", sym.Lane(self.svg, edge=-1))
        self.add_sym("lane_R", sym.Lane(self.svg, edge=1))

        self.add_sym("lane_split_R", sym.LaneJoiner(self.svg))
        self.add_sym("lane_split_L", sym.LaneJoiner(self.svg, flipx=True))
        self.add_sym("lane_join_R", sym.LaneJoiner(self.svg, flipy=True))
        self.add_sym("lane_join_L", sym.LaneJoiner(self.svg, True, True))

    def add_sym(self, id, sym):
        new_sym = self.svg.symbol(id=id)
        new_sym.add(sym.get_sym())
        self.svg.defs.add(new_sym)

    def add_hwy(self):
        hwy = Highway(self)
        self.cur_horiz += self.hwy_offset
        self.hwys.append(hwy)
        return hwy

    def render(self, fmt = 'svg'):
        for hwy in self.hwys:
            # Determine direction
            exit_nums = []
            for r in hwy.rows:
                try:
                    exit_nums.append(int(r.links[0].number))
                except (KeyError, IndexError, TypeError, ValueError):
                    pass

            total_diff = 0
            for i in range(len(exit_nums)-1):
                total_diff += exit_nums[i] - exit_nums[i+1]

            if(total_diff < 0):
                hwy.rows.reverse()
                hwy.flipped = True

            hwy.render(fmt)
            if(fmt == 'text'):
                print('='*(self.hwy_offset+self.text_buffer))

    def save(self, filename):
        return self.svg.saveas(filename)

class Highway:
    def __init__(self, diagram):
        self.dwg = diagram
        self.horiz = diagram.cur_horiz
        self.rows = []
        self.flipped = False

    def add_row(self, offset = None):
        row = Row(self.dwg, self)
        if(offset is not None):
            row.offset = offset
        self.rows.append(row)
        return row

    def render(self, fmt = 'svg'):
        for idx in range(len(self.rows)):
            r = self.rows[idx]
            try:
                r.adjust_offset(self.rows[idx+1])
            except IndexError:
                pass

            row = r.render(fmt, idx)
            if(fmt == 'text'):
                print(row)
            else:
                self.dwg.svg.add(row)

class Row:
    def __init__(self, dwg, hwy):
        self.lanes = []
        self.links = []
        self.caps = []
        self.lane_diff = 0
        self.offset = 0
        self.dwg = dwg
        self.svg = dwg.svg
        self.gs = dwg.gs
        self.hwy = hwy

    def get_flip(self):
        return 1 if self.hwy.flipped else -1

    def adjust_offset(self, next_row):
        if(next_row):
            # Is there a difference in lanes between this lane and next?
            lane_diff = len(next_row.lanes) - len(self.lanes)
            lane_adj = 0

            # Check if we already have something that adds a lane
            # (Entrances, or Exits for flipped highways)
            for (idx, l) in enumerate(self.links):
                if(isinstance(l, Exit if self.hwy.flipped else Entrance)):
                    # If we have one and need a lane added, use it
                    if(lane_diff > 0):
                        self.caps.append(idx)
                        lane_diff-=1
                        # If it's a left-side lane, it'll eat up one col of offset
                        if(l.side != self.get_flip()):
                            lane_adj -= 1
            # ...and, in the next lane, for something that removes a lane
            for (idx, l) in enumerate(next_row.links):
                if(isinstance(l, Entrance if self.hwy.flipped else Exit)):
                    if(lane_diff < 0):
                        next_row.caps.append(idx)
                        lane_diff+=1
                        # Left-side removers will leave empty below them, adding a col of offset
                        if(l.side != self.get_flip()):
                            lane_adj += 1

            # If we still have a difference, note it so we can add a joiner
            if(lane_diff):
                rel_row = next_row if lane_diff < 0 else self
                rel_row.lane_diff = lane_diff

            # TODO: This will always eliminate rightmost lanes
            # Sometimes we might know that it's the left lane instead?
            next_row.offset = self.offset + lane_adj

    def render(self, fmt, idx):
        self.idx = idx
        pos = (self.offset, self.idx)

        text_bits = {}

        if(self.lane_diff):
            lj = LaneJoiner(self.lane_diff, 1)
            lj.set_row(self)
            self.extras = [lj]
        else:
            self.extras = []

        if(fmt == 'text'):
            text_bits['left_links'] = [l.render('text', None) for l in self.links if l.side == -1 and not isinstance(l, Label)]
            text_bits['left_extras'] = [e.render('text', None) for e in self.extras if e.side == -1]
        else:
            g = self.svg.g(id='row' + str(self.idx))

        text_bits['lanes'] = ''
        for (i, l) in enumerate(self.lanes):
            lane = l.render(fmt, i)
            if(fmt == 'svg'):
                g.add(lane)
            else:
                text_bits['lanes'] += lane

        if(fmt == 'text'):
            text_bits['right_links'] = [l.render('text', None) for l in self.links if l.side == 1 and not isinstance(l, Label)]
            text_bits['right_extras'] = [e.render('text', None) for e in self.extras if e.side == 1]
        else:
            counts = {-1: 0, 1: 0}
            for e in self.extras:
                e.set_row(self)
                g.add(e.render(fmt, counts[e.side]))
                counts[e.side] += 1
            for (idx, l) in enumerate(self.links):
                l.set_row(self)
                g.add(l.render(fmt, counts[l.side], (idx in self.caps)))
                counts[l.side] += 2

            return g

        if fmt == 'text':
            after = 'right' if self.hwy.flipped else 'left'
            before = 'left' if self.hwy.flipped else 'right'
            num_buffer_things = len(text_bits[before+'_links']) + len(text_bits[before+'_extras'])

            row = ' '*(self.dwg.text_buffer + self.offset - num_buffer_things)
            row += ''.join(text_bits[before+'_links']) + ''.join(text_bits[before+'_extras'])
            row += text_bits['lanes']
            row += ''.join(text_bits[after+'_extras']) + ''.join(text_bits[after+'_links'])
            row += ''.join([l.render('text', None) for l in self.links if isinstance(l, Label)])
            return row


    def add_lane(self, el):
        el.set_row(self)
        self.lanes.append(el)

    def add_link(self, el):
        el.set_row(self)
        self.links.append(el)

class Element:
    sidename = {-1: 'L', 1: 'R'}
    def set_row(self, row):
        self.row = row
        self.svg = row.svg

    def get_flip(self):
        return self.row.get_flip()

    def get_flipside(self):
        return self.side * self.get_flip()

    def get_relpos(self):
        return (self.row.hwy.horiz + self.row.offset, self.row.idx)

    def get_symbol(self, id, relpos, pos, prefixes = []):
        sym = self.svg.use('#' + id, (relpos[0]+pos, relpos[1]))
        sym.scale(self.row.gs)
        prefixes.append(id)
        prefixes.append(sym.get_id())
        sym.attribs['id'] = '_'.join(prefixes)
        return sym

class Lane(Element):
    edge_name = {-1: 'L', 0: 'mid', 1: 'R'}
    def __init__(self, type = None):
        self.type = type

    def edge(self, pos):
        if(pos == 0):
            return -1 # Leftmost
        elif(pos == len(self.row.lanes) - 1):
            return 1 # Rightmost
        else:
            return 0

    def render(self, fmt, pos):
        edge = self.edge(pos)

        if(fmt == 'text'):
            if(edge == -1):
                return '┨┆'
            elif(edge == 1):
                return '┠'
            else:
                return '┆'

        return self.get_symbol(
            'lane_' + self.edge_name[edge],
            self.get_relpos(), pos
        )

class Link(Element):
    def __init__(self, side):
        self.side = side

    def get_pos(self, idx):
        return -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

class Ramp(Link):
    def __init__(self, type = None, number = None):
        self.number = number
        super().__init__(type)

    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            if is_cap:
                return self.cap_chars[self.get_flipside()]
            else:
                return self.ramp_chars[self.get_flip()][self.side]

        pos = -(idx+1) if self.get_flipside() == -1 else len(self.row.lanes) + idx

        nameparts = [self.typestr]
        if(is_cap):
            nameparts.append('cap')
        if(self.row.hwy.flipped):
            nameparts.append('flip')
        nameparts.append(self.sidename[self.get_flipside()])
        return self.get_symbol(
            '_'.join(nameparts),
            relpos, pos
        )

class Exit(Ramp):
    ramp_chars = {
        -1: {1:'⤦',-1:'⤥'}, # Southbound
        1: {-1:'⤣',1:'⤤'}, # Northbound
    }
    cap_chars = {-1:'╲',1:'╱'}
    typestr = 'exit'

class Entrance(Ramp):
    ramp_chars = {
        -1: {1:'⇘',-1:'⇙'}, # Southbound
        1: {-1:'⇗',1:'⇖'}, # Northbound
    }
    cap_chars = {-1:'╱',1:'╲'}
    typestr = 'entrance'

class Label(Element):
    def __init__(self, side, type, text):
        self.side = side
        self.text = text
        self.type = type

    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()

        if(fmt == 'text'):
            return ('->' if self.type=='exit' else '<-') + self.abbreviate(self.text)

        anchor = 'end' if(self.side != self.get_flip()) else 'start'
        pos = -(idx+1) if self.side != self.get_flip() else len(self.row.lanes) + idx
        our_pos = (pos+1) if(self.side != self.get_flip()) else pos

        #TODO: Figure out a baseline to center this vertically as well
        return self.svg.text(self.text,
            insert=(
                (relpos[0] + our_pos)*self.row.gs,
                (relpos[1] + 0.75)*self.row.gs
            ),
            text_anchor=anchor
        )

    def abbreviate(self, name):
        numeric = re.match(r'(.*: )?((?:North|South|East|West)\w* )?(\d+\w+)( (?:Street|Avenue))?$', name)
        if numeric:
            return numeric.group(3)

        return name

class LaneJoiner(Link):
    def __init__(self, diff, side):
        self.diff = diff
        self.direction = copysign(1, diff) # Reduction = -1, Addition = 1
        super().__init__(side)

    def render(self, fmt, idx):
        if(fmt == 'text'):
            lines = '-'*(abs(self.diff)-1)
            return ('/' + lines if(self.direction == self.get_flipside()) else lines + '\\')

        relpos = self.get_relpos()
        pos = self.get_pos(idx)
        sym = self.get_symbol(
            '_'.join([
                'lane',
                'split' if self.diff > 0 else 'join',
                self.sidename[self.side]
            ]),
            relpos, pos
        )
        width = abs(self.diff)
        xpos = relpos[0] + pos
        sym.scale(width, 1)
        if(width > 1):
            sym.translate(-xpos*(1-1/width), 0)
        return sym
