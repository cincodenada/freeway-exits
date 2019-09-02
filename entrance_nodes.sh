#!/bin/bash -x
OSMFILTER=./osmfilter
if [ -z $1 ] || [ -z $2 ]; then
    echo "Usage:"
    echo "./entrance_nodes.sh <input.osm> <nodelist> [chunk_size]"
    exit 0
fi

infile=$1
nodes=$2
if [ -z "$3" ]; then
  chunk=500
else
  chunk=$3
fi

mergefiles=""
lines=`wc -l $nodes | cut -d\  -f1`
numchunks=0
for startline in `seq 1 $chunk $lines`; do
  outfile="${nodes}_${startline}.osm"
  echo "Extracting $chunk starting at $startline to $outfile..."
  $OSMFILTER $infile \
    --keep="`tail -n+$startline $nodes | head -n$chunk | perl -ne 'BEGIN { print "\@ndref"; } chomp; print "=$_ "'`" \
    --drop="highway=motorway_link" > $outfile
  mergefiles="$mergefiles --rx $outfile"
  numchunks=$(($numchunks+1))
done

if [ $numchunks -eq 1 ]; then
    echo "Copying only file to merged"
    cp ${nodes}_1.osm ${nodes}.merged.osm
else
    mergecmd=$(for i in $(seq 2 $numchunks); do echo -n " --merge"; done)
    echo "osmosis $mergefiles $mergecmd --wx ${nodes}_merged.osm"
    osmosis $mergefiles $mergecmd --wx ${nodes}.merged.osm
fi
