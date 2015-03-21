# xplane2fgfs
Tools to get airport data from Xplane in FlightGear

## get_airport.py
The tool to get a single aurport by its ICAO code
```
$ python get_airport.py 
Usage: get_airport.py <airport_ICAO_code>
```
As get_airport.py outputs airport data to STDOUT consider redirecting output
into file of other program. e.g.:
```
python get_airport.py ULSG > ULSG.dat
```
## apt_fetcher.py
The tool to get *all* airports
available at X-plane gateway (http://gateway.x-plane.com/).
Usage:
```
pyton apt_fetcher.py > apt.dat
```

*I strongly recommend redirecting as the tool outputs all airports APT data
to STDOUT. This was made to follow KISS concept.*
