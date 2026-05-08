MAP BUILDER
===========

Build an interactive map of places — cafés, museums, schools, parks,
anything — in any European city or municipality. The result is a
single HTML file you open in your browser.

Double-click the build script for your system to get started.


INSTALL PYTHON
--------------
You need Python 3.8 or later.

  Mac / Linux:  Go to https://www.python.org/downloads/
                and run the installer.

  Windows:      Open the Microsoft Store, search for "Python",
                and click Install. Alternatively, go to
                https://www.python.org/downloads/ and tick
                "Add Python to PATH" before installing.

Already have Python? Skip this step. Not sure? Install anyway,
it won't break anything.


RUN THE TOOL
------------
  Mac:      Double-click build-MAC.command.
            If macOS blocks it, right-click the file and choose Open.

  Windows:  Double-click build-WINDOWS.bat.

  Linux:    Open a terminal in this folder and run
            ./build-LINUX.sh

The first run takes a few minutes. The tool downloads map data
the first time only, later runs are fast.

You'll be asked three questions:

  1. Which city or municipality? Search by name.
  2. What types of places? Cafés, schools, parks, and so on.
  3. Which version of the map data? Press Enter for the default.

When the tool finishes, the map opens in your browser. The file
is also saved in output_map/.


IMPORT FROM CSV
---------------
You can also build a map from a previously exported CSV file.

  1. Use the CSV export button in an existing map to save a file.
  2. Place the CSV file in the input_data/ folder.
  3. Run the tool as usual (double-click the build script).

The tool detects the CSV automatically and skips the city and
category questions. If several CSV files are present, the most
recently modified one is used.

City boundaries are looked up automatically. If a city name
exists in more than one country, you will be asked to pick
the correct one.

To go back to the normal interactive mode, remove or move the
CSV file out of input_data/.


IF SOMETHING GOES WRONG
-----------------------
macOS won't open the file:
  Right-click the file, choose Open, confirm in the dialog.
  Once is enough.

Windows shows a blue SmartScreen warning:
  Click "More info", then "Run anyway".

"Python not found" or similar:
  Python isn't installed, or the computer can't find it. Reinstall,
  and on Windows tick "Add Python to PATH".

Nothing happens, or the window closes immediately:
  Open a terminal (Mac: Terminal, Windows: Command Prompt) and run
  the script from there. Error messages will show up.

The map is empty or sparse:
  The category may have no data in that municipality. Try a larger
  city or a broader category.


START OVER
----------
Open the reset/ folder and double-click the right file:

  Mac:      reset-MAC.command
  Windows:  reset-WINDOWS.bat
  Linux:    ./reset-LINUX.sh

This deletes downloaded data and previous maps. Python is left alone.


WHERE THE DATA COMES FROM
-------------------------
- City boundaries:  Eurostat GISCO LAU 2024
                    https://ec.europa.eu/eurostat/web/gisco
- Places:           Overture Maps Foundation
                    https://overturemaps.org
- Background:       OpenStreetMap

All sources are open and freely available.


NEED HELP?
----------
Email magnus.liistamo@humangeo.su.se
Department of Human Geography, Stockholm University.


CREDITS
-------
Code is licensed under Apache 2.0. See LICENSE.

Built as part of STARTUP (Sustainable Transitions: Action Research
and Training in Urban Perspective). This project has received
funding from the European Union's Horizon Europe research and
innovation programme under Grant Agreement No 101178523.

Views and opinions expressed are those of the author(s) only and
do not necessarily reflect those of the European Union or the
granting authority. Neither the European Union nor the granting
authority can be held responsible for them.

Project repository:
https://github.com/Liistamo/overture-eu-mapper
