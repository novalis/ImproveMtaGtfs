#!/usr/bin/python


#special thanks to the Carnegie Deli and the Roxy Delicatessen for
#being at the right places at the right time.

import sys

f = open("extra-stops.txt")
extra_stops = []
for line in f:
    extra_stops.append(line.strip())
f.close()


f = open("stops.txt")
stops = []
header = f.readline().strip()
if header != "stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,zone_id,stop_url,location_type,parent_station":
    print "Can't add entranes to stops.txt, because the format has changed"
    sys.exit(1)
for line in f:
    stops.append(line.strip())
f.close()

f = open("stops.txt", "w")
f.write(header + "\n")
for stop in stops:
    f.write(stop + "\n")
for stop in extra_stops:
    f.write(stop + "\n")

f.close()
