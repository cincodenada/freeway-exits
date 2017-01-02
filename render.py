import svgwrite
from svgwrite import mm
from math import copysign
import symbols as sym

class Diagram:
    text_buffer = 5
    hwy_spacing = 750
    def __init__(self, gridsize):
        self.gs = gridsize
        self.svg = svgwrite.Drawing(filename='out.svg', debug=True)
        self.hwys = []
        self.cur_horiz = 0
        self.hwy_offset = self.hwy_spacing/gridsize

        self.add_sym("exit_R", sym.Ramp(self.svg, False, False))
        self.add_sym("entrance_R", sym.Ramp(self.svg, False, True))
        self.add_sym("exit_L", sym.Ramp(self.svg, True, False))
        self.add_sym("entrance_L", sym.Ramp(self.svg, True, True))

        self.add_sym("exit_cap_R", sym.LaneEnd(self.svg, False, False))
        self.add_sym("entrance_cap_R", sym.LaneEnd(self.svg, False, True))
        self.add_sym("exit_cap_L", sym.LaneEnd(self.svg, True, False))
        self.add_sym("entrance_cap_L", sym.LaneEnd(self.svg, True, True))

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

            hwy.render()

    def save(self):
        return self.svg.save()

class Highway:
    def __init__(self, diagram):
        self.dwg = diagram
        self.horiz = diagram.cur_horiz
        self.rows = []
        self.flipped = False

    def add_row(self, offset = None):
        row = Row(self.dwg, self, len(self.rows))
        if(offset is not None):
            row.offset = offset
        self.rows.append(row)
        return row

    def render(self, fmt = 'svg'):
        for idx in range(len(self.rows)):
            r = self.rows[idx]
            try:
                self.rows[idx+1].adjust_offset(r)
            except IndexError:
                pass

            row = r.render(fmt)
            if(fmt == 'text'):
                print(row)
            else:
                self.dwg.svg.add(row)

class Row:
    def __init__(self, dwg, hwy, id):
        self.lanes = []
        self.links = []
        self.caps = []
        self.lane_diff = 0
        self.offset = 0
        self.dwg = dwg
        self.svg = dwg.svg
        self.gs = dwg.gs
        self.hwy = hwy
        self.id = id

    def adjust_offset(self, last_row):
        if(last_row):
            lane_diff = len(self.lanes) - len(last_row.lanes)
            lane_adj = 0
            for (idx, l) in enumerate(last_row.links):
                if(isinstance(l, Entrance)):
                    if(lane_diff > 0):
                        last_row.caps.append(idx)
                        lane_diff-=1
                        if(l.side == -1):
                            lane_adj -= 1
            for (idx, l) in enumerate(self.links):
                if(isinstance(l, Exit)):
                    if(lane_diff < 0):
                        self.caps.append(idx)
                        lane_diff+=1
                        if(l.side == -1):
                            lane_adj += 1
            if(lane_diff):
                rel_row = self if lane_diff < 0 else last_row
                rel_row.lane_diff = lane_diff

            # TODO: This will always eliminate rightmost lanes
            # Sometimes we might know that it's the left lane instead?
            self.offset = last_row.offset + lane_adj

    def render(self, fmt):
        pos = (
            self.offset,
            self.id,
        )

        if(self.lane_diff):
            lj = LaneJoiner(self.lane_diff, 1)
            lj.set_row(self)
            self.extras = [lj]
        else:
            self.extras = []

        if(fmt == 'text'):
            left_links = [l.render('text', None) for l in self.links if l.side == -1 and not isinstance(l, Label)]
            left_extras = [e.render('text', None) for e in self.extras if e.side == -1]

            num_left_things = len(left_links) + len(left_extras)
            row = ' '*(self.dwg.text_buffer + self.offset - num_left_things)
            row += ''.join(left_links) + ''.join(left_extras)
        else:
            g = self.svg.g(id='row' + str(self.id))

        for (i, l) in enumerate(self.lanes):
            lane = l.render(fmt, i)
            if(fmt == 'svg'):
                g.add(lane)
            else:
                row += lane

        if(fmt == 'text'):
            right_links = [l.render('text', None) for l in self.links if l.side == 1 or isinstance(l, Label)]
            right_extras = [e.render('text', None) for e in self.extras if e.side == 1]
            row += ''.join(right_extras) + ''.join(right_links)
            return row
        else:
            counts = {-1: 0, 1: 0}
            for e in self.extras:
                e.set_row(self)
                g.add(e.render(fmt, counts[e.side]))
                counts[e.side] += 1
            for (idx, l) in enumerate(self.links):
                l.set_row(self)
                g.add(l.render(fmt, counts[l.side], (idx in self.caps)))
                counts[l.side] += 1

            return g

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
        return -1 if self.row.hwy.flipped else 1

    def get_flipside(self):
        return self.side * self.get_flip()

    def get_relpos(self):
        return (self.row.hwy.horiz + self.row.offset, self.row.id)

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

class Exit(Ramp):
    chars = {
        False: {-1:'╗',1:'╔'},
        True: {-1:'╲',1:'╱'},
    }
    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            return self.chars[is_cap][self.get_flipside()]

        if(self.row.hwy.flipped):
            rot = 90 if self.side == -1 else 180
        else:
            rot = 0 if self.side == -1 else 270
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

        return self.get_symbol(
            'exit_' + ('cap_' if is_cap else '') + self.sidename[self.side],
            relpos, pos
        )

class Entrance(Ramp):
    chars = {
        False: {-1:'╔',1:'╗'},
        True: {-1:'╱',1:'╲'},
    }
    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            return self.chars[is_cap][self.get_flipside()]

        if(self.row.hwy.flipped):
            rot = 0 if self.side == -1 else 270
        else:
            rot = 90 if self.side == -1 else 180
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

        return self.get_symbol(
            'entrance_' + ('cap_' if is_cap else '') + self.sidename[self.side],
            relpos, pos
        )

class Label(Element):
    def __init__(self, side, type, text):
        self.side = side
        self.text = text
        self.type = type

    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()

        if(fmt == 'text'):
            return ('->' if self.type=='exit' else '<-') + self.text

        anchor = 'end' if(self.side == -1) else 'start'
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx
        our_pos = (pos+1) if(self.side == -1) else pos

        #TODO: Figure out a baseline to center this vertically as well
        return self.svg.text(self.text,
            insert=(
                (relpos[0] + our_pos)*self.row.gs,
                (relpos[1] + 0.5)*self.row.gs
            ),
            text_anchor=anchor
        )

class LaneJoiner(Link):
    def __init__(self, diff, side):
        self.diff = diff
        self.direction = copysign(1, diff) # Reduction = -1, Addition = 1
        super().__init__(side)

    def render(self, fmt, idx):
        if(fmt == 'text'):
            lines = '-'*(abs(self.diff)-1)
            return ('/' + lines if(self.direction == self.get_flipside()) else lines + '\\')

        return self.get_symbol(
            '_'.join([
                'lane',
                'split' if self.diff > 0 else 'join',
                self.sidename[self.side]
            ]),
            self.get_relpos(), self.get_pos(idx)
        )
