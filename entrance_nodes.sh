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

lines=`wc -l $nodes | cut -d\  -f1`
for startline in `seq 1 $chunk $lines`; do
  outfile="${nodes}_${startline}.osm"
  echo "Extracting $chunk starting at $startline to $outfile..."
  ./osmfilter $infile --keep="`tail -n+$startline $nodes | head -n$chunk | perl -ne 'BEGIN { print "\@ndref"; } chomp; print "=$_ "'`" > $outfile
done
