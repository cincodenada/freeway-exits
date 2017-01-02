import svgwrite
from svgwrite import mm
from math import copysign
import symbols as sym

sidename = {-1: 'L', 1: 'R'}

class Diagram:
    text_buffer = 5
    def __init__(self, gridsize):
        self.gs = gridsize
        self.rows = []
        self.dwg = svgwrite.Drawing(filename='out.svg', debug=True)

        self.add_sym("exit_R", sym.Ramp(self.dwg, False, False))
        self.add_sym("entrance_R", sym.Ramp(self.dwg, False, True))
        self.add_sym("exit_L", sym.Ramp(self.dwg, True, False))
        self.add_sym("entrance_L", sym.Ramp(self.dwg, True, True))

        self.add_sym("exit_cap_R", sym.LaneEnd(self.dwg, False, False))
        self.add_sym("entrance_cap_R", sym.LaneEnd(self.dwg, False, True))
        self.add_sym("exit_cap_L", sym.LaneEnd(self.dwg, True, False))
        self.add_sym("entrance_cap_L", sym.LaneEnd(self.dwg, True, True))

    def add_sym(self, id, sym):
        new_sym = self.dwg.symbol(id=id)
        new_sym.add(sym.get_sym())
        self.dwg.defs.add(new_sym)

    def render(self, fmt = 'svg'):
        cur_offset = 0
        last_row = None
        for idx in range(len(self.rows)):
            r = self.rows[idx]
            r.flipped = True
            try:
                self.rows[idx+1].adjust_offset(r)
            except IndexError:
                pass

            row = r.render(fmt)
            if(fmt == 'text'):
                print(row)
            else:
                self.dwg.add(row)

    def save(self):
        return self.dwg.save()

    def add_row(self, offset = None):
        row = Row(self, len(self.rows))
        if(offset is not None):
            row.offset = offset
        self.rows.append(row)
        return row

class Row:
    def __init__(self, drawing, id):
        self.lanes = []
        self.links = []
        self.extras = []
        self.caps = []
        self.offset = 0
        self.text_buffer = drawing.text_buffer
        self.dwg = drawing.dwg
        self.gs = drawing.gs
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
                            lane_adj += 1
            for (idx, l) in enumerate(self.links):
                if(isinstance(l, Exit)):
                    if(lane_diff < 0):
                        self.caps.append(idx)
                        lane_diff+=1
                        if(l.side == -1):
                            lane_adj += 1
            if(lane_diff):
                rel_row = self if lane_diff < 0 else last_row
                lj = LaneJoiner(lane_diff, 1)
                lj.set_row(rel_row)
                rel_row.extras.append(lj)

            # TODO: This will always eliminate rightmost lanes
            # Sometimes we might know that it's the left lane instead?
            self.offset = last_row.offset + lane_adj

    def render(self, fmt):
        pos = (
            self.offset,
            self.id,
        )

        if(fmt == 'text'):
            left_links = [l.render('text', None) for l in self.links if l.side == -1 and not isinstance(l, Label)]
            left_extras = [e.render('text', None) for e in self.extras if e.side == -1]

            num_left_things = len(left_links) + len(left_extras)
            row = ' '*(self.text_buffer + self.offset - num_left_things)
            row += ''.join(left_links) + ''.join(left_extras)
        else:
            g = self.dwg.g(id='row' + str(self.id))

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
    bez_circle_dist = 0.551915024494
    def set_row(self, row):
        self.row = row
        self.dwg = row.dwg

    def get_flip(self):
        return -1 if self.row.flipped else 1

    def get_flipside(self):
        return self.side * self.get_flip()

    def get_relpos(self):
        return (self.row.offset, self.row.id)

    def get_symbol(self, id, relpos, pos, prefixes = []):
        sym = self.dwg.use('#' + id, (relpos[0]+pos, relpos[1]))
        sym.scale(self.row.gs)
        prefixes.append(id)
        prefixes.append(sym.get_id())
        sym.attribs['id'] = '_'.join(prefixes)
        return sym

class Lane(Element):
    def __init__(self, type = None):
        self.type = type

    def edge(self, pos):
        if(pos == 0):
            return -1 # Leftmost
        elif(pos == len(self.row.lanes) - 1):
            return 1 # Rightmost

    def render(self, fmt, pos):
        edge = self.edge(pos)

        if(fmt == 'text'):
            if(edge == -1):
                return '┨┆'
            elif(edge == 1):
                return '┠'
            else:
                return '┆'


        relpos = self.get_relpos()
        g = self.dwg.g()
        g.add(self.dwg.rect(
            insert=(
                (relpos[0] + pos)*self.row.gs,
                relpos[1]*self.row.gs
            ),
            size=(
                self.row.gs,
                self.row.gs
            ),
            fill='gray',
        ))

        left_side = self.dwg.line(
            start=(
                (relpos[0] + pos)*self.row.gs,
                relpos[1]*self.row.gs
            ),
            end=(
                (relpos[0] + pos)*self.row.gs,
                (relpos[1] + 1)*self.row.gs
            ),
            stroke='black',
            stroke_width=1
        )
        if(edge != -1):
            left_side.dasharray([2,2])
        g.add(left_side)

        right_side = self.dwg.line(
            start=(
                (relpos[0] + (pos+1))*self.row.gs,
                relpos[1]*self.row.gs
            ),
            end=(
                (relpos[0] + (pos+1))*self.row.gs,
                (relpos[1] + 1)*self.row.gs
            ),
            stroke='black',
            stroke_width=1
        )
        if(edge != 1):
            right_side.dasharray([2,2])
        g.add(right_side)
        return g

class Link(Element):
    def __init__(self, side):
        self.side = side

class Exit(Link):
    chars = {
        False: {-1:'╗',1:'╔'},
        True: {-1:'╲',1:'╱'},
    }
    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            return self.chars[is_cap][self.get_flipside()]

        if(self.row.flipped):
            rot = 90 if self.side == -1 else 180
        else:
            rot = 0 if self.side == -1 else 270
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

        return self.get_symbol(
            'exit_' + ('cap_' if is_cap else '') + sidename[self.side],
            relpos, pos
        )

class Entrance(Link):
    chars = {
        False: {-1:'╔',1:'╗'},
        True: {-1:'╱',1:'╲'},
    }
    def render(self, fmt, idx, is_cap = False):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            return self.chars[is_cap][self.get_flipside()]

        if(self.row.flipped):
            rot = 0 if self.side == -1 else 270
        else:
            rot = 90 if self.side == -1 else 180
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

        return self.get_symbol(
            'entrance_' + ('cap_' if is_cap else '') + sidename[self.side],
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
        return self.dwg.text(self.text,
            insert=(
                (relpos[0] + our_pos)*self.row.gs,
                (relpos[1] + 0.5)*self.row.gs
            ),
            text_anchor=anchor
        )

class LaneJoiner(Element):
    def __init__(self, diff, side):
        self.diff = diff
        self.direction = copysign(1, diff) # Reduction = -1, Addition = 1
        self.side = side

    def render(self, fmt, pos):
        if(fmt == 'text'):
            lines = '-'*(abs(self.diff)-1)
            return '/' + lines if(self.direction == self.get_flipside()) else lines + '\\'
        else:
            return self.row.dwg.g()
