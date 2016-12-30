import svgwrite
from svgwrite import mm

class Diagram:
    def __init__(self, gridsize):
        self.gs = gridsize
        self.rows = []
        self.dwg = svgwrite.Drawing(filename='out.svg', debug=True)
        self.cur_row = 0

    def render(self, fmt = 'svg'):
        cur_pos = 0
        for r in self.rows:
            r.render(fmt, (0, cur_pos))
            cur_pos += self.gs

    def save(self):
        return self.dwg.save()

    def add_row(self, start_pos):
        row = Row(self, self.cur_row, start_pos)
        self.rows.append(row)
        self.cur_row =+ 1
        return row

class Row:
    def __init__(self, drawing, id, start_pos):
        self.members = []
        self.start_pos = start_pos
        self.dwg = drawing.dwg
        self.gs = drawing.gs
        self.id = id

    def render(self, fmt, pos):
        if(fmt == 'svg'):
            self.g = self.dwg.add(self.dwg.g(id='row' + str(self.id)))
        else:
            row = " "*self.start_pos
        cur_pos = self.start_pos
        for m in self.members:
            member = m.render(fmt, pos, cur_pos)
            if(fmt == 'svg'):
                self.g.add(member)
            else:
                row += member
            cur_pos += 1
        if(fmt == 'text'):
            print(row)

    def add_element(self, el, insert = False):
        if(isinstance(insert, bool)):
            pos = 0 if insert else len(self.members)
        else:
            pos = insert

        el.set_row(self)
        self.members.insert(pos, el)

class Element:
    bez_circle_dist = 0.551915024494
    def set_row(self, row):
        self.row = row
        self.dwg = row.dwg

    def render_arc(self, relpos, pos, rot=0):
        g = self.dwg.g()
        path = self.dwg.path(d=('M',(relpos[0] + pos*self.row.gs), relpos[1]))
        path.push('c',
            0, (self.bez_circle_dist*self.row.gs),
            (1 - self.bez_circle_dist)*self.row.gs, self.row.gs,
            self.row.gs, self.row.gs
        )
        path.push('l', 0, -self.row.gs)
        path.push('l', -self.row.gs, 0)
        path.fill(color='gray')
        g.add(path)
        path = self.dwg.path(d=('M',(relpos[0] + pos*self.row.gs), relpos[1]))
        path.push('c',
            0, (self.bez_circle_dist*self.row.gs),
            (1 - self.bez_circle_dist)*self.row.gs, self.row.gs,
            self.row.gs, self.row.gs
        )
        path.fill(opacity=0)
        path.stroke(color='black',width=1)
        g.add(path)
        g.rotate(rot, (relpos[0] + (pos+0.5)*self.row.gs, relpos[1] + 0.5*self.row.gs))
        return g

class Lane(Element):
    def render(self, fmt, relpos, pos):
        if(fmt == 'text'):
            return '║'

        is_leftmost = (pos == self.row.start_pos)
        is_rightmost = (pos == len(self.row.members) - 1)

        g = self.dwg.g()
        g.add(self.dwg.rect(
            insert=(
                (relpos[0] + pos*self.row.gs),
                relpos[1]
            ),
            size=(
                self.row.gs,
                self.row.gs
            ),
            fill='gray',
        ))

        left_side = self.dwg.line(
            start=(
                (relpos[0] + pos*self.row.gs),
                relpos[1]
            ),
            end=(
                (relpos[0] + pos*self.row.gs),
                (relpos[1] + self.row.gs)
            ),
            stroke='black',
            stroke_width=1
        )
        if(not is_leftmost):
            left_side.dasharray([2,2])
        g.add(left_side)

        right_side = self.dwg.line(
            start=(
                (relpos[0] + (pos+1)*self.row.gs),
                relpos[1]
            ),
            end=(
                (relpos[0] + (pos+1)*self.row.gs),
                (relpos[1] + self.row.gs)
            ),
            stroke='black',
            stroke_width=1
        )
        if(not is_rightmost):
            right_side.dasharray([2,2])
        g.add(right_side)
        return g

class Exit(Element):
    def render(self, fmt, relpos, pos):
        if(fmt == 'text'):
            return '╗' if (pos == self.row.start_pos + 1) else '╔'
        rot = 90 if (pos == self.row.start_pos + 1) else 0
        return self.render_arc(relpos, pos, rot)

class Entrance(Element):
    def render(self, fmt, relpos, pos):
        if(fmt == 'text'):
            return '╔' if (pos == self.row.start_pos + 1) else '╗'
        return self.render_arc(relpos, pos, 180)

class Label(Element):
    def __init__(self, text):
        self.text = text

    def render(self, fmt, relpos, pos):
        is_left = (pos == self.row.start_pos)
        if(fmt == 'text'):
            return '*' if(is_left) else self.text
        anchor = 'end' if is_left else 'start'
        our_pos = (pos+1) if is_left else pos

        #TODO: Figure out a baseline to center this vertically as well
        return self.dwg.text(self.text,
            insert=(
                (relpos[0] + our_pos*self.row.gs),
                (relpos[1] + self.row.gs*0.5)
            ),
            text_anchor=anchor
        )
