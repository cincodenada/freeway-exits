class Symbol:
    bez_circle_dist = 0.551915024494
    def __init__(self, dwg, flipx=False, flipy=False):
        self.flipx = flipx
        self.flipy = flipy
        self.dwg = dwg
        self.g = dwg.g()

    def get_sym(self):
        self.render()
        self.g.scale((-1 if self.flipx else 1, -1 if self.flipy else 1))
        self.g.translate((-1 if self.flipx else 0, -1 if self.flipy else 0)) 

        return self.g

class Ramp(Symbol):
    width=2
    def __init__(self, dwg, flipx=False, flipy=False, radius=0.25, cap_color='gray'):
        self.radius = radius
        self.cap_color = cap_color
        super().__init__(dwg, flipx, flipy)

    def render(self):
        ramp_path = self.dwg.path(d=('M',0,0))
        ramp_path.push('c',
            0, self.radius*self.bez_circle_dist,
            self.radius*(1-self.bez_circle_dist), self.radius,
            self.radius, self.radius
        )
        ramp_path.push('l', 1-self.radius, 0)
        ramp_path.push('l', 0, 1-self.radius)
        ramp_path.push('l', -(1-self.radius), 0)
        ramp_path.push('c',
            -self.radius*self.bez_circle_dist, 0,
            -self.radius, -self.radius*(1-self.bez_circle_dist),
            -self.radius, -self.radius
        )
        ramp_path.fill(color='gray')
        self.g.add(ramp_path)

        self.g.add(self.dwg.rect(
            insert=(1,self.radius),
            size=(1,1-self.radius),
            fill=self.cap_color,
        ))

        ramp_outline = self.dwg.path(d=('M',0,0))
        ramp_outline.push('c',
            0, self.radius*self.bez_circle_dist,
            self.radius*(1-self.bez_circle_dist), self.radius,
            self.radius, self.radius
        )
        ramp_outline.push('l', 2-self.radius, 0)
        ramp_outline.push('m', 0, 1-self.radius)
        ramp_outline.push('l', -(2-self.radius), 0)
        ramp_outline.push('c',
            -self.radius*self.bez_circle_dist, 0,
            -self.radius, -self.radius*(1-self.bez_circle_dist),
            -self.radius, -self.radius
        )
        ramp_outline.stroke(color='black',width=0.05)
        ramp_outline.fill(opacity=0)
        self.g.add(ramp_outline)

class LaneEnd(Symbol):
    width=2
    def __init__(self, dwg, flipx=False, flipy=False, cap_color='gray'):
        self.cap_color = cap_color
        super().__init__(dwg, flipx, flipy)

    def render(self):
        path = self.dwg.path(d=('M',0,0))
        path.push('c',
            0, self.bez_circle_dist,
            (1 - self.bez_circle_dist), 1,
            1, 1
        )
        path.push('l', 0, -1)
        path.push('l', -1, 0)
        path.fill(color='gray')
        self.g.add(path)

        self.g.add(self.dwg.rect(
            insert=(1,0),
            size=(1,1),
            fill=self.cap_color,
        ))

        path = self.dwg.path(d=('M',0,0))
        path.push('c',
            0, self.bez_circle_dist,
            1 - self.bez_circle_dist, 1,
            1, 1
        )
        path.fill(opacity=0)
        path.stroke(color='black',width=0.05)
        self.g.add(path)

class Lane(Symbol):
    def __init__(self, dwg, flipx=False, flipy=False, edge=0):
        self.edge = edge
        super().__init__(dwg, flipx, flipy)

    def render(self):
        self.g.add(self.dwg.rect(
            insert=(0,0),
            size=(1,1),
            fill='gray',
        ))

        left_side = self.dwg.line(
            start=(0,0),
            end=(0,1),
            stroke='black',
            stroke_width=0.05
        )
        if(self.edge != -1):
            left_side.dasharray([0.1,0.1])
        self.g.add(left_side)

        right_side = self.dwg.line(
            start=(1,0),
            end=(1,1),
            stroke='black',
            stroke_width=0.05
        )
        if(self.edge != 1):
            right_side.dasharray([0.1,0.1])
        self.g.add(right_side)

class LaneJoiner(Symbol):
    def render(self):
        path = self.dwg.path(d=('M',0,0))
        path.push('l',1,1)
        path.push('l',-1,0)
        path.fill(color='gray')
        self.g.add(path)

        path = self.dwg.path(d=('M',0,0))
        path.push('l',1,1)
        path.stroke(color='black',width=0.05)
        self.g.add(path)
