#!/usr/bin/python

import os
import sys
import csv
from datetime import date, time

if not (os.path.exists("in") and os.path.isdir("in")):
    print "Directory 'in' must exist and must contain the contents of the MTA Bus Company zip file"
    sys.exit(1)

if not os.path.exists("out"):
    os.mkdir("out")

f = open(os.path.join("in", "stops.txt"))
stops_txt = open(os.path.join("out", "stops.txt"), "w")
reader = csv.reader(f)


#process stops.txt

header = None
for row in reader:
    if not header:
        header = row
        stops_txt.write("stop_id,stop_name,stop_lat,stop_lon\n")
        continue
    d = {}
    for id, col in zip(header, row):
        d[id] = col

    if "," in d['Location']:
        d['Location'] = '"%s"' % d['Location']

    stops_txt.write("%(ATIS ID)s,%(Location)s,%(Lat)s,%(Long)s\n" % d)


#process routes.txt

f = open(os.path.join("in", "routes.txt"))
routes_txt = open(os.path.join("out", "routes.txt"), "w")
routes_txt.write("route_id,route_short_name,route_long_name,route_type\n")

trips_txt = open(os.path.join("out", "trips.txt"), "w")
trips_txt.write("route_id,service_id,trip_id\n")

stop_times_txt = open(os.path.join("out", "stop_times.txt"), "w")
stop_times_txt.write("trip_id,arrival_time,departure_time,stop_id,stop_sequence\n")

calendar_txt = open(os.path.join("out", "calendar.txt"), "w")
calendar_txt.write("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n")

calendar_dates_txt = open(os.path.join("out", "calendar_dates.txt"), "w")
calendar_dates_txt.write("service_id,date,exception_type\n")

reader = csv.reader(f)

def gtfsify_date(date):
    return date.replace("/","")

def to_python_date(gtfs_date):

    if "/" in gtfs_date:
        gtfs_date = gtfsify_date(gtfs_date)
    return date(int(gtfs_date[:4]), int(gtfs_date[4:6]), int(gtfs_date[6:8]))

wsu_to_gtfsdays = {"W" : "1,1,1,1,1,0,0",
                   "V" : "1,1,1,1,0,0,1", #days before weekdays
                   "S" : "0,0,0,0,0,1,0",
                   "U" : "0,0,0,0,0,0,1",
                   "E" : "1,1,1,1,1,1,1",
                   "H" : "0,0,0,0,0,0,0",
                   "F" : "0,0,0,0,1,0,0",
                   }

date_exceptions = [
("U","20100531"),
("U","20100705"),
("U","20100906"),
("U","20101125"),
("U","20101225"),

("U","20110101"),
("S","20110221"),
("U","20110530"),
("U","20110704"),
("U","20110905"),
("U","20111124"),

("S","20120220"),
("U","20120528"),
("U","20120704"),
("U","20120903"),
("U","20121122"),
("U","20121225"),

("U","20130101"),
("S","20120218"),
("U","20130527"),
("U","20130704"),
("U","20130903"),
("U","20131128"),
("U","20131225"),

("U","20140101"),
("S","20120217"),
("U","20140526"),
("U","20140704"),
("U","20140901"),
("U","20141127"),
("U","20141225"),
]

date_ranges = {}

counter = 0

routes = {}
seen_service_ids = set()

stop_id = None

def is_bad_route_name(route):
    if len(route) == 1:
        return True
    if route in ('FS', 'GS', 'SIR'):
        return True
    if 'AIRTRAIN' in route:
        return True
    return False

while 1:
    try:
        row = reader.next()
    except StopIteration:
        break

    type = row[0]
    if type == '1':
        #new route/direction
        type, direction, route, schedule, _ = row
        if is_bad_route_name(route):
            #subway line, move along until we see a bus or the SI ferry
            while 1:
                try:
                    row = reader.next()
                except StopIteration:
                    sys.exit(0)
                type = row[0]
                if type == '1':
                    type, direction, route, schedule, _ = row

                    if not is_bad_route_name(route):
                        break

        if schedule == 'M':
            #I have no idea what M means, but this will at least not break things too badly.
            schedule = 'U'
            
        if not schedule in wsu_to_gtfsdays:
            import pdb;pdb.set_trace()

        route_short_name = route
    elif type == '2':
        #new subroute
        type, src, dest, route_long_name, start_date, end_date, _ = row
        if end_date == 'none':
            end_date = '21000703'
        #this might require a new set of dates. Let's find out.
        range = date_ranges.get((start_date, end_date))
        if not range:
            counter += 1 
            date_ranges[(start_date, end_date)] = "%s" % counter
            
            range = "%s" % counter

        service_id = "%s%s" % (schedule, range)
        if not service_id in seen_service_ids:
            seen_service_ids.add(service_id)
            calendar_txt.write("%s,%s,%s,%s\n" % (service_id, wsu_to_gtfsdays[schedule], gtfsify_date(start_date), gtfsify_date(end_date)))

            #write calendar exceptions, if applicable
            if schedule in 'USW':
                start_date = to_python_date(start_date)
                end_date = to_python_date(end_date)

                for schedule_day, gtfs_date in date_exceptions:
                    if start_date <= to_python_date(gtfs_date) <= end_date:
                        calendar_dates_txt.write("%s,%s,2\n" % (service_id, gtfs_date))
                        calendar_dates_txt.write("%s%s,%s,1\n" % (schedule_day, range, gtfs_date))

        if schedule == 'H':
            #holidays, for the Staten Island Ferry.  This assumption could be wrong.
            for schedule_day, gtfs_date in date_exceptions:
                calendar_dates_txt.write("%s,%s,1\n" % (service_id, gtfs_date))

        #a new route, if necessary
        route_key = (route_short_name, route_long_name)
        if route_key in routes:
            route_id = routes[route_key]
        else:
            counter += 1
            route_id = "%s" % counter
            routes[route_key] = route_id
            if route_short_name == 'AIRTRAIN': 
                route_short_name = "" #contained in route_long_name
                mode = 0
            elif route_short_name == 'SIF': 
                mode = 4
            else:
                mode = 3

            if route_long_name.startswith(route_short_name + " - "):
                route_long_name = route_long_name[len(route_short_name + " - "):]
            if "LTD" in route_short_name and "LTD" in route_long_name:
                route_long_name = route_long_name[len(route_short_name + "  "):]

            routes_txt.write("%s,%s,%s,%s\n" % (route_id,route_short_name,route_long_name, mode))

        stops = []
        stop_id = None
    elif type == "3":
        #stop prototype
        old_stop_id = stop_id
        type, stop_id, is_tp, _1, _2, _3, _4, _5 = row
        is_tp = is_tp == "Y"
        if old_stop_id == stop_id:
            if is_tp:
                stops.pop() #replace previous stop
            else:
                continue #previous stop is tp, so use it
        stops.append((stop_id, is_tp))

    elif type == "5":
        if route_long_name.startswith("AIRTRAIN"):
            #sadly, there is no real airtrain data
            continue
        #trip

        cur_proto = 0

        counter += 1
        trip_id = "%s" % counter

        #don't write the trip yet in case we need to move it back in time

        adjustment = 0
        old_stop_id = None
    elif type == "6":        

        type, stop_id, minutes_past_midnight, depart_or_arrive = row
        minutes_past_midnight = int(minutes_past_midnight)
        minutes_past_midnight += adjustment

        if minutes_past_midnight < 0:
            #this ought to be taken out and shot.

            #We have to go back in time and change it to a
            #positive time on a different day (or set of days).  Why
            #does ATIS even allow this sort of nonsense?

            #OK, so we invent then ecessary prior schedules, if necessary.  Then we add 24h
            #to all stop times on this trip.  

            #FIXME: this will be wrong on days after holidays

            if schedule == 'S':
                schedule = 'F'
            elif schedule == 'W':
                schedule = 'V'
            elif schedule == 'U':
                schedule = 'S'
                service_id = "%s%s" % (schedule, range)

            if schedule != 'S':
                service_id = "%s%s" % (schedule, range)
                if service_id in seen_service_ids:
                    continue
                seen_service_ids.add(service_id)
                calendar_txt.write("%s,%s,%s,%s\n" % (service_id, wsu_to_gtfsdays[schedule], gtfsify_date(start_date), gtfsify_date(end_date)))

            adjustment = 1440
            minutes_past_midnight += adjustment

        if cur_proto == 0:
            trips_txt.write("%s,%s,%s\n" % (route_id,service_id,trip_id))

        #timepoint -- write all prior non-timepoints

        while cur_proto < len(stops):
            stop_id, is_tp = stops[cur_proto]
            cur_proto += 1
            if is_tp:
                break
            stop_times_txt.write("%s,,,%s,%s\n" % (trip_id, stop_id, cur_proto))

        if old_stop_id == stop_id:
            continue
        old_stop_id = stop_id
        stop_time = "%02d:%02d:00" % (minutes_past_midnight / 60, minutes_past_midnight % 60)

        stop_times_txt.write("%s,%s,%s,%s,%s\n" % (trip_id, stop_time, stop_time, stop_id, cur_proto))

