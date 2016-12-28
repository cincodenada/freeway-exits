import svgwrite
from svgwrite import mm

class Drawing:
    def __init__(self, gridsize):
        self.gs = gridsize
        self.rows = []
        self.dwg = svgwrite.Drawing(filename='out.svg', debug=True)
        self.cur_row = 0

    def render(self):
        cur_pos = 0
        for r in self.rows:
            r.render((0, cur_pos))
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

    def render(self, pos):
        self.g = self.dwg.add(self.dwg.g(id='row' + str(self.id)))
        cur_pos = self.start_pos
        for m in self.members:
            self.g.add(m.render(pos, cur_pos))
            cur_pos += 1

    def add_element(self, el, insert = False):
        if(isinstance(insert, bool)):
            pos = 0 if insert else len(self.members)
        else:
            pos = insert

        el.set_row(self)
        self.members.insert(pos, el)

class Element:
    def set_row(self, row):
        self.row = row
        self.dwg = row.dwg

class Lane(Element):
    def render(self, relpos, pos):
        g = self.dwg.g()
        g.add(self.dwg.line(
            start=(
                (relpos[0] + pos*self.row.gs)*mm,
                relpos[1]*mm
            ),
            end=(
                (relpos[0] + pos*self.row.gs)*mm,
                (relpos[1] + self.row.gs)*mm
            ),
            stroke='black',
            stroke_width=1
        ))
        g.add(self.dwg.line(
            start=(
                (relpos[0] + (pos+1)*self.row.gs)*mm,
                relpos[1]*mm
            ),
            end=(
                (relpos[0] + (pos+1)*self.row.gs)*mm,
                (relpos[1] + self.row.gs)*mm
            ),
            stroke='black',
            stroke_width=1
        ))
        return g

class Exit(Element):
    def render_arc(self, relpos, pos):
        path = self.dwg.path(d=('M',(relpos[0] + pos*self.row.gs), relpos[1]))
        path.push_arc(
            target=(
                (relpos[0] + (pos+1)*self.row.gs)*mm,
                (relpos[1] + self.row.gs)*mm
            ),
            r=self.row.gs,
            rotation=90
        )
        return path

    def render(self, relpos, pos):
        ycoords = [relpos[1], relpos[1] + self.row.gs]
        if(pos == self.row.start_pos + 1):
            ycoords.reverse()
        return self.dwg.line(
             start=(
                 (relpos[0] + (pos)*self.row.gs)*mm,
                 ycoords[0]*mm
             ),
             end=(
                 (relpos[0] + (pos+1)*self.row.gs)*mm,
                 ycoords[1]*mm
             ),
             stroke='black',
             stroke_width=1
        )

class Entrance(Element):
    def render(self, relpos, pos):
        return self.dwg.line(
             start=(
                 (relpos[0] + (pos+1)*self.row.gs)*mm,
                 relpos[1]*mm
             ),
             end=(
                 (relpos[0] + (pos)*self.row.gs)*mm,
                 (relpos[1] + self.row.gs)*mm
             ),
             stroke='black',
             stroke_width=1
        )

class Label(Element):
    def __init__(self, text):
        self.text = text

    def render(self, relpos, pos):
        is_left = (pos == self.row.start_pos)
        anchor = 'end' if is_left else 'start'
        our_pos = (pos+1) if is_left else pos

        #TODO: Figure out a baseline to center this vertically as well
        return self.dwg.text(self.text,
            insert=(
                (relpos[0] + our_pos*self.row.gs)*mm,
                (relpos[1] + self.row.gs*0.5)*mm
            ),
            text_anchor=anchor
        )
