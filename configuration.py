"""
<configuration.py is to help the user easily adjust the print parameters.>
Copyright (C) <2020>  <Luke Vandenberghe>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
Last updated: October 26, 2020
"""

#layer height (mm)
layer_height = 0.15

#print speed mm/s
print_speed = 40

#infill_percentage (only supports 100% currently)
infill_percentage = 100

#temperature of hotend (celsius)
print_temperature = 200

#retraction length (mm)
retraction_length = 2.0

#retraction speed (mm/s)
retraction_speed = 30

#nozzle diameter (mm)
nozzle_diameter = 0.4

#wall line count
wall_line_count = 1

#start gcode (when modifying make sure the variable names remain the same)
start_gcode = ("M82 ;absolute extrusion mode\n" + 
               "G21 ; set units to millimeters\n" + 
               "G90 ; use absolute positioning\n" + 
               "M104 S{print_temperature} \n" + 
               "G28 X0;X endstop\n" + 
               "G28 Z0 ; move Z to endstop\n" + 
               "M109 S{print_temperature} \n" + 
               "G0 Z{layer_height} ; Raise\n" + 
               "G92 E0 ; zero the E length\n" + 
               "M107 ; turn off fan\n" + 
               ";MESH: {stl_file_address}\n" + 
               ";LAYER COUNT: {layer_count}\n")

#end gcode (when modifying make sure the variable names remain the same)
end_gcode = ("G1 Z{raise_height}\n" + 
             "G1 X0; home X \n" + 
             "M104 S0 \n" +
             "M84 ; disable motors\n" + 
             ";end of gcode\n")

#flavor (I wrote the gcode based off of the marlin firmware)
flavor = "Marlin"

#header of gcode
header = (";Flavor:{flavor}\n" + 
          ";Layer height: {layer_height}\n \n")

#location (mm) you can modify this in the gui as well
location_x = 0
location_y = 0
location_z = 0

#rotation (degrees) you can modify this in the gui as well
rotation_x = 0
rotation_y = 0
rotation_z = 0

#cylinder diameter (mm)
cylinder_diameter = 60

#cylinder length (mm)
cylinder_length = 250

#delta y (mm) - the change in y of the printer after one full revolution of 
#cylinder. Consult guide for more details.
delta_y = 97

#filament diameter
filament_diameter = 1.75

#Infill orientation options (0, 90) - alternating or (45, 135) - alternating
infill_orientation = 45

#Imports
import slicer_gui as sg

if __name__ == '__main__':
    slicer = sg.slicer_gui()
    slicer.run()