class Symbol:
    bez_circle_dist = 0.551915024494
    def __init__(self, dwg, flipx, flipy):
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
    def __init__(self, dwg, flipx, flipy, radius=0.25):
        self.radius = radius
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

        ramp_outline = self.dwg.path(d=('M',0,0))
        ramp_outline.push('c',
            0, self.radius*self.bez_circle_dist,
            self.radius*(1-self.bez_circle_dist), self.radius,
            self.radius, self.radius
        )
        ramp_outline.push('l', 1-self.radius, 0)
        ramp_outline.push('m', 0, 1-self.radius)
        ramp_outline.push('l', -(1-self.radius), 0)
        ramp_outline.push('c',
            -self.radius*self.bez_circle_dist, 0,
            -self.radius, -self.radius*(1-self.bez_circle_dist),
            -self.radius, -self.radius
        )
        ramp_outline.stroke(color='black',width=0.05)
        ramp_outline.fill(opacity=0)
        self.g.add(ramp_outline)

class LaneEnd(Symbol):
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

        path = self.dwg.path(d=('M',0,0))
        path.push('c',
            0, self.bez_circle_dist,
            1 - self.bez_circle_dist, 1,
            1, 1
        )
        path.fill(opacity=0)
        path.stroke(color='black',width=0.05)
        self.g.add(path)