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
## update_apt_file.py
The tool to get *all* airports available at X-plane gateway
(http://gateway.x-plane.com/) and generate a single "apt.dat" file
with all airports in it.
Individual airports fetched from gateway are saved in files and
are not re-downloaded if they do not need updating.
This reduces load on X-plane's server.

Usage:
```
pyton update_apt_file.py
```

Individual airports are saved in ```<ICAO>.dat``` files
in ```airports/``` directory which is created in current work directory (CWD).
Version of latest airports downloaded is stored in ```latest.json``` in CWD.
resulting file ```apt.dat``` is generated in CWD. If a file with this name
already exists, it's being renamed into ```apt.dat.bak```.

Set ```DEBUG``` environment variable to non-empty value to have more logging.
Example:
```
DEBUG=yes pyton update_apt_file.py
```
