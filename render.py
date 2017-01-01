import svgwrite
from svgwrite import mm
from math import copysign

sidename = {-1: 'L', 1: 'R'}

class Diagram:
    bez_circle_dist = 0.551915024494
    def __init__(self, gridsize):
        self.gs = gridsize
        self.rows = []
        self.dwg = svgwrite.Drawing(filename='out.svg', debug=True)

        # Create defs
        ramp_radius = 0.25

        exit_r = self.dwg.symbol(id="exit_R")
        exit_r.add(self.make_ramp(ramp_radius, False, False))
        self.dwg.defs.add(exit_r)

        entrance_r = self.dwg.symbol(id="entrance_R")
        entrance_r.add(self.make_ramp(ramp_radius, False, True))
        self.dwg.defs.add(entrance_r)

        exit_l = self.dwg.symbol(id="exit_L")
        exit_l.add(self.make_ramp(ramp_radius, True, False))
        self.dwg.defs.add(exit_l)

        entrance_l = self.dwg.symbol(id="entrance_L")
        entrance_l.add(self.make_ramp(ramp_radius, True, True))
        self.dwg.defs.add(entrance_l)

        exit_cap_r = self.dwg.symbol(id="exit_cap_R")
        exit_cap_r.add(self.make_lane_end(False, False))
        self.dwg.defs.add(exit_cap_r)

        entrance_cap_r = self.dwg.symbol(id="entrance_cap_R")
        entrance_cap_r.add(self.make_lane_end(False, True))
        self.dwg.defs.add(entrance_cap_r)

        exit_cap_l = self.dwg.symbol(id="exit_cap_L")
        exit_cap_l.add(self.make_lane_end(True, False))
        self.dwg.defs.add(exit_cap_l)

        entrance_cap_l = self.dwg.symbol(id="entrance_cap_L")
        entrance_cap_l.add(self.make_lane_end(True, True))
        self.dwg.defs.add(entrance_cap_l)

    def make_ramp(self, ramp_radius, flipx=False, flipy=False):
        g = self.dwg.g()
        ramp_path = self.dwg.path(d=('M',0,0))
        ramp_path.push('c',
            0, ramp_radius*self.bez_circle_dist,
            ramp_radius*(1-self.bez_circle_dist), ramp_radius,
            ramp_radius, ramp_radius
        )
        ramp_path.push('l', 1-ramp_radius, 0)
        ramp_path.push('l', 0, 1-ramp_radius)
        ramp_path.push('l', -(1-ramp_radius), 0)
        ramp_path.push('c',
            -ramp_radius*self.bez_circle_dist, 0,
            -ramp_radius, -ramp_radius*(1-self.bez_circle_dist),
            -ramp_radius, -ramp_radius
        )
        ramp_path.fill(color='gray')
        g.add(ramp_path)

        ramp_outline = self.dwg.path(d=('M',0,0))
        ramp_outline.push('c',
            0, ramp_radius*self.bez_circle_dist,
            ramp_radius*(1-self.bez_circle_dist), ramp_radius,
            ramp_radius, ramp_radius
        )
        ramp_outline.push('l', 1-ramp_radius, 0)
        ramp_outline.push('m', 0, 1-ramp_radius)
        ramp_outline.push('l', -(1-ramp_radius), 0)
        ramp_outline.push('c',
            -ramp_radius*self.bez_circle_dist, 0,
            -ramp_radius, -ramp_radius*(1-self.bez_circle_dist),
            -ramp_radius, -ramp_radius
        )
        ramp_outline.stroke(color='black',width=0.05)
        ramp_outline.fill(opacity=0)
        g.add(ramp_outline)

        g.scale((-1 if flipx else 1, -1 if flipy else 1))
        g.translate((-1 if flipx else 0, -1 if flipy else 0))

        return g

    def make_lane_end(self, flipx=False, flipy=False):
        g = self.dwg.g()

        path = self.dwg.path(d=('M',0,0))
        path.push('c',
            0, self.bez_circle_dist,
            (1 - self.bez_circle_dist), 1,
            1, 1
        )
        path.push('l', 0, -1)
        path.push('l', -1, 0)
        path.fill(color='gray')
        g.add(path)
        path = self.dwg.path(d=('M',0,0))
        path.push('c',
            0, self.bez_circle_dist,
            1 - self.bez_circle_dist, 1,
            1, 1
        )
        path.fill(opacity=0)
        path.stroke(color='black',width=0.05)
        g.add(path)

        g.scale((-1 if flipx else 1, -1 if flipy else 1))
        g.translate((-1 if flipx else 0, -1 if flipy else 0))

        return g


    def render(self, fmt = 'svg'):
        cur_offset = 0
        last_row = None
        for r in self.rows:
            r.flipped = True
            r.adjust_offset(last_row)
            row = r.render(fmt)
            if(fmt == 'text'):
                print(row)
            else:
                self.dwg.add(row)
            last_row = r

    def save(self):
        return self.dwg.save()

    def add_row(self):
        row = Row(self, len(self.rows))
        self.rows.append(row)
        return row

class Row:
    def __init__(self, drawing, id):
        self.lanes = []
        self.links = []
        self.extras = []
        self.offset = 0
        self.dwg = drawing.dwg
        self.gs = drawing.gs
        self.id = id

    def adjust_offset(self, last_row):
        if(last_row):
            lane_diff = len(self.lanes) - len(last_row.lanes)
            lane_adj = 0
            for l in last_row.links:
                if(isinstance(l, Entrance)):
                    if(lane_diff > 0):
                        lane_diff-=1
                        if(l.side == -1):
                            lane_adj += 1
            for l in self.links:
                if(isinstance(l, Exit)):
                    if(lane_diff < 0):
                        lane_diff+=1
                        if(l.side == -1):
                            lane_adj += 1
            if(lane_diff):
                lj = LaneJoiner(lane_diff, 1)
                lj.set_row(self)
                self.extras.append(lj)

            # TODO: This will always eliminate rightmost lanes
            # Sometimes we might know that it's the left lane instead?
            self.offset = last_row.offset + lane_adj

    def render(self, fmt):
        pos = (
            self.offset,
            self.id,
        )

        if(fmt == 'text'):
            left_links = [l.render('text', None) for l in self.links if l.side == -1]
            left_extras = [e.render('text', None) for e in self.extras if e.side == -1]

            row = ''
            num_left_things = len(left_links) + len(left_extras)
            if(num_left_things < self.offset):
                row += ' '*(self.offset - num_left_things)
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
            right_links = [l.render('text', None) for l in self.links if l.side == 1]
            right_extras = [e.render('text', None) for e in self.extras if e.side == 1]
            row += ''.join(right_extras) + ''.join(right_links)
            return row
        else:
            counts = {-1: 0, 1: 0}
            for e in self.extras:
                e.set_row(self)
                g.add(e.render(fmt, counts[e.side]))
                counts[e.side] += 1
            for l in self.links:
                l.set_row(self)
                g.add(l.render(fmt, counts[l.side]))
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
        prefixes.append(sym.get_id())
        sym.attribs['id'] = '_'.join(prefixes)
        return sym

class Lane(Element):
    def __init__(self, type = None):
        self.type = type

    def edge(self, pos):
        if(pos == self.row.offset):
            return -1 # Leftmost
        elif(pos == len(self.row.lanes) - 1):
            return 1 # Rightmost

    def render(self, fmt, pos):
        if(fmt == 'text'):
            return '║'

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
        if(self.edge(pos) != -1):
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
        if(self.edge(pos) != 1):
            right_side.dasharray([2,2])
        g.add(right_side)
        return g

class Link(Element):
    def __init__(self, side):
        self.side = side

class Exit(Link):
    def render(self, fmt, idx):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            return '╗' if self.get_flipside() == -1 else '╔'
        if(self.row.flipped):
            rot = 90 if self.side == -1 else 180
        else:
            rot = 0 if self.side == -1 else 270
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

        return self.get_symbol(
            'exit_' + sidename[self.side],
            relpos, pos,
            ['exit', sidename[self.side]]
        )

class Entrance(Link):
    def render(self, fmt, idx):
        relpos = self.get_relpos()
        if(fmt == 'text'):
            return '╔' if self.get_flipside() == -1 else '╗'
        if(self.row.flipped):
            rot = 0 if self.side == -1 else 270
        else:
            rot = 90 if self.side == -1 else 180
        pos = -(idx+1) if self.side == -1 else len(self.row.lanes) + idx

        return self.get_symbol(
            'entrance_' + sidename[self.side],
            relpos, pos,
            ['entrance', sidename[self.side]]
        )

class Label(Element):
    def __init__(self, text):
        self.text = text

    def render(self, fmt, pos):
        relpos = self.get_relpos()

        is_left = (pos == self.row.offset)
        if(fmt == 'text'):
            return '*' if(is_left) else self.text
        anchor = 'end' if is_left else 'start'
        our_pos = (pos+1) if is_left else pos

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
