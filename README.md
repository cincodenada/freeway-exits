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

My end goal is to be able to generate a diagram of I-5 through Seattle that is
virtually identical to the original diagram. From there, I start taking it
elsewhere and find more ways to break it.

[orig]: https://www.reddit.com/r/SeattleWA/comments/5i5ww9/i_get_annoyed_when_i_cant_figure_out_what_lane_i/ "Original post, just southbound"
[v2]: https://www.reddit.com/r/SeattleWA/comments/5i5ww9/i_get_annoyed_when_i_cant_figure_out_what_lane_i/ "Improved post, both directions"
[osmc]: https://gitlab.com/osm-c-tools/osmctools "osmctools GitLab"
