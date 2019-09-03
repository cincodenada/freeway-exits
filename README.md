Highway Diagrammer
==================

A long while ago, a user who has sadly since deleted their account created 
some really neat [simplified][orig] [diagrams][v2] of I-5 through Seattle 
and posted them to /r/SeattleWA.

As a big fan of bending data to my will, I looked at the diagram and thought,
*you know, I bet I could generate that from OpenStreetMap data*.

Many weekends and countless hours later, I've made some progress, but have much
yet to improve. I've had to hack additional filters into [`osmfilter`][osmc] to
pull out the data I need, and dealt with countless inane combinations of entrances
and exits, teasing details out of the OSM data that obviously isn't always
organized nicely for this kind of minimalist diagramming.

My first goal is to be able to generate a diagram of I-5 through Seattle that is
virtually identical to the original diagram. From there, I start taking it
elsewhere and find more ways to break it.

Current status is pretty dang messy - the basics are in place and it generates
a diagram, but there are plenty of missing labels and some stub highways, and
the SVG it generates is, uh, far from optimized. It's somewhere between
proof-of-concept and MVP at this point.

But, as of this writing, here's what it generates for the Seattle area, compared
to the original diagram that I'm aiming for, more or less. The only editing I
did here is to chop out the relevant sections of freeway and space them out
sensibly:

Generated | Original
-|-
![Generated diagram of Seattle freeways](seattle.png) |![Original diagram of Seattle freeways](inspiration.png)

Usage
-----

This is not guaranteed to be up to date, but last time I updated it, this is
how things worked. You'll need OSM data, some osm tools, and Python 3.
 
To start, you need OSM data! If you have some laying around you can use that,
otherwise there are various sites to get extracts, or you can download a chunk
from JOSM or what have you. [GeoFabrik](https://download.geofabrik.de/) is an
excellent source for extracts by geographic area.

You'll also need [osmfilter](https://wiki.openstreetmap.org/wiki/Osmfilter),
which the extract script is just a very light wrapper around. If your extract
isn't in a format supported by `osmfilter` (namely, `.osm` or `.o5m`), you'll
need to use `osmconvert` to get it into one of those formats.

For instance, for my reference of I-5 through Seattle, I downloaded the
GeoFabrik extract for [Washington State](waextract), and then converted it to
the proper format with:

```shell
osmconvert washington-latest.osm.pbf --out-o5m > washington.o5m`
```

There are a few extracts needed, this is probably more complicated than it
strictly needs to be and may be simplified eventually but for now, here's what
i got. This also requires [osmosis](osmosis) for the last step.
```shell
# Optional: create and enter a Python venv
python -m virtualenv -p python3 VENV
source VENV/bin/activate
# Install Python requirements (currently just svgwrite)
pip install -r requirements.txt
# Generate an SVG
./extract.sh washington.o5m
./exits.py --svg out.svg
```

And you'll get an (very large, probably inefficient) SVG with a diagram out, if
all goes well!

There are other options available, use `--help` for details. By default
`exit.sh` will output a bunch of debug to STDERR and a textual representation to
STDOUT, both mostly useful for debugging. To output an svg, specify a filename
with the `--svg` argument. If you want to render a highway that is not I-5, use
the `--highway` argument to specify an OSM ref name to use (defaults to `I 5`).

Auxillary Nodes
---------------

The above will result in a diagram with a lot of missing labels for entrance
ramps, because entrances don't usually have metadata attached to them. To work
around this, there are a couple more scripts to extract the streets that
entrances and exits come from and use them to fill in the missing labels.

Extracting these requires a custom build of osmfilter (I haven't bothered trying
to get my flag upstream yet). The `osmfilter` subrepo has the requisite version
from my fork, and there's a symlink to where the `osmfilter` binary will be
generated. You'll need to build the subrepo:

```shell
cd osmctools
autoreconf --install
./configure
make
```

Then cd back into the root, run the extracts, and then re-run the main script:

```shell
cd ..
./exits.py --dump-nodes > link_nodes
./entrance_nodes.sh washingon.o5m link_nodes
./exits.py --aux-prefix link_nodes --svg out.svg
```

This extract takes a while (the extract for Washington State took several
minutes on my Core i7), because my patches aren't terribly optimized.  I've
deemed it not worth the effort to dig more into `osmfilter.c` to make them so,
because I'd rather just set it running and wait it out.

[orig]: https://www.reddit.com/r/SeattleWA/comments/5i5ww9/i_get_annoyed_when_i_cant_figure_out_what_lane_i/ "Original post, just southbound"
[v2]: https://www.reddit.com/r/SeattleWA/comments/5ipdkg/another_cool_diagram/ "Improved post, both directions"
[osmc]: https://gitlab.com/osm-c-tools/osmctools "osmctools GitLab"
[waextract]: https://download.geofabrik.de/north-america/us/washington.html
[osmosis]: https://wiki.openstreetmap.org/wiki/Osmosis
