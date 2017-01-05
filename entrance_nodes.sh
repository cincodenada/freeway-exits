./osmfilter /store/data/geo/osm/washington-latest.o5m --keep="`tail -n+501 entrance_nodes | head -n500 | perl -ne 'BEGIN { print "\@ndref"; } chomp; print "=$_ "'`" > entrance_1000
