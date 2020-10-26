"""
<gcode_parser.py prepares Gcode.>
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

#Imports
import cylindrical_slicer as cs
import numpy as np

class gcode_parser:
    def __init__(self, gcode_file_address:str, layer_height:float, 
                 print_speed:int, infill_percentage:int, print_temperature:int,
                 retraction_length:float, retraction_speed:int, 
                 nozzle_diameter:float, wall_line_count:int, start_gcode:str, 
                 end_gcode:str, flavor:str, header:str, stl_file_address:str, 
                 location_x:float, location_y:float, location_z:float,
                 rotation_x:int, rotation_y:int, rotation_z:int,
                 cylinder_diameter:float, delta_y:float, filament_diameter:float,
                 infill_orientation:int):
        
        #User input values
        self.gcode_file_address = gcode_file_address
        self.layer_height = layer_height
        self.print_speed = print_speed
        self.infill_percentage = infill_percentage
        self.print_temperature = print_temperature
        self.retraction_length = retraction_length
        self.retraction_speed = retraction_speed
        self.nozzle_diameter = nozzle_diameter
        self.wall_line_count = wall_line_count
        self.start_gcode = start_gcode
        self.end_gcode = end_gcode
        self.flavor = flavor
        self.header = header
        self.stl_file_address = stl_file_address
        self.location_x = location_x
        self.location_y = location_y
        self.location_z = location_z
        self.rotation_x = rotation_x
        self.rotation_y = rotation_y
        self.rotation_z = rotation_z
        self.cylinder_diameter = cylinder_diameter
        self.delta_y = delta_y
        self.filament_diameter = filament_diameter
        self.infill_orientation = infill_orientation
        
        #Instance of slicer class
        self.slicer = cs.cylindrical_slicer(self.stl_file_address, 
                                            self.nozzle_diameter, 
                                            self.rotation_x, 
                                            self.rotation_y, 
                                            self.rotation_z, 
                                            self.location_x, 
                                            self.location_y, 
                                            self.location_z, 
                                            self.cylinder_diameter, 
                                            self.delta_y)
     
        #Get the number of layers needed to print the model
        difference = self.slicer.max_radius - (self.cylinder_diameter / 2)
        self.layer_count = int(difference / self.layer_height) - 1
        
        #error threshold
        self.epsilon = 0.0000001
          
    def create_gcode(self) -> str:
        E = 0 # extrusion length mm
        feed_rate_G1 = self.print_speed * 60 #mm/min
        feed_rate_G0 = self.print_speed * 60 #mm/min
        feed_rate_retraction = self.retraction_speed * 60 #mm/min
        slice_orientation = self.infill_orientation #degrees
        gcode_body = ""
        current_layer = 0
        print("slicing model...")
        while current_layer < self.layer_count:
            current_layer += 1
            r = self.layer_height * current_layer + (self.cylinder_diameter / 2)
            gcode_body += f";layer:{current_layer}\n"
            
            edges = self.slicer.gather_edges(r)
            if str(edges) == "error":
                print("Error: No intersection points found.")
                return "error"
            walls = self.slicer.create_loops(edges)
            if str(walls) == "error":
                print("Error: Unable to make closed loop.")
                return "error"
            
            #Print the outer and inner borders of the model    
            for i in range(self.wall_line_count):
                if i == 0:
                    gcode_body += f";outer-wall\n"
                gcode_body += f";wall:{i + 1}\n"
                scale = 1 + i * 0.02 
                wall = self.slicer.scale_loops(scale,
                                               walls[0], 
                                               walls[1])
                previous_point = np.array([0, 0])
                
                for edge in wall:
                    x_2, x_1 = (np.round(edge[3], 5), 
                                np.round(edge[0], 5)) 
                    y_2, y_1 = (np.round(edge[4], 5), 
                                np.round(edge[1], 5))
                    z_2, z_1 = (np.round(edge[5], 5), 
                                np.round(edge[2], 5))
                    #Retraction
                    if ((abs(previous_point[0] - x_1) > self.epsilon) and 
                        (abs(previous_point[1] - y_1) > self.epsilon)):
                        gcode_body += ("G92 E0\n"+
                                       f"G1 E-{self.retraction_length} F{feed_rate_retraction}\n")
                        gcode_body += (f"G0 F{feed_rate_G0} " + 
                                       f"X{x_1} Y{y_1} Z{z_1}\n")
                        gcode_body += (f"G1 E0.1200 F{feed_rate_retraction}\n" +
                                        "G92 E0\n")
                        E = 0
                    distance = np.sqrt((y_2 - y_1) ** 2 + (x_2 - x_1) ** 2)
                    volume = distance * self.layer_height * self.nozzle_diameter
                    E += volume / (self.filament_diameter ** 2)
                    gcode_body += (f"G1 F{feed_rate_G1} " +
                                   f"X{x_2} Y{y_2} Z{z_2} E{E}\n")
                    previous_point = np.array([x_2, y_2])
                    
            #Alternate the slice orientation     
            if (slice_orientation == 0) or (slice_orientation == 45):
                slice_orientation += 90
            else:
                slice_orientation -= 90
            
            infill = self.slicer.infill(wall, slice_orientation) 
            gcode_body += ";infill\n"
            previous_line_bounds = np.array([0, 0])
            for line_bound in infill:
                x_2, x_1 = (np.round(line_bound[3], 5), 
                            np.round(line_bound[0], 5)) 
                y_2, y_1 = (np.round(line_bound[4], 5), 
                            np.round(line_bound[1], 5))
                z_2, z_1 = (np.round(line_bound[5], 5), 
                            np.round(line_bound[2], 5))
                x_squared = (previous_line_bounds[0] - x_1) ** 2
                y_squared = (previous_line_bounds[1] - y_1) ** 2
                distance_next = float(np.sqrt(x_squared + y_squared))
                spacing = self.nozzle_diameter * 1.18
                
                #Retraction
                if (abs(distance_next - spacing) > spacing and 
                    abs(distance_next - spacing) > spacing):
                    gcode_body += ("G92 E0\n"+
                                   f"G1 E-{self.retraction_length} F{feed_rate_retraction}\n")
                    gcode_body += (f"G0 F{feed_rate_G0} " + 
                                   f"X{x_1} Y{y_1} Z{z_1}\n")
                    gcode_body += (f"G1 E0.1200 F{feed_rate_retraction}\n" +
                                    "G92 E0\n")
                    E = 0
                else:
                    gcode_body += f"G0 F{feed_rate_G0} X{x_1} Y{y_1} Z{z_1} \n"
                distance = np.sqrt((y_2 - y_1) ** 2 + (x_2 - x_1) ** 2)
                volume = distance * self.layer_height * self.nozzle_diameter
                E += volume / (self.filament_diameter ** 2) 
                gcode_body += (f"G1 F{feed_rate_G1} " + 
                               f"X{x_2} Y{y_2} Z{z_2} E{E} \n")
                previous_line_bounds = np.array([x_2, y_2])
                
            print("layer:", current_layer,"/", self.layer_count)
            
        end_height = round(self.layer_height * (self.layer_count + 2))
        gcode_body += self.end_gcode.format(raise_height = end_height)
        gcode_header = self.header.format(flavor = self.flavor, 
                                          layer_height = self.layer_height) 
        gcode_start = self.start_gcode.format(print_temperature = self.print_temperature, 
                                              layer_height = self.layer_height, 
                                              stl_file_address = self.stl_file_address,
                                              layer_count = self.layer_count)
        gcode = gcode_header + gcode_start + gcode_body 
        print("Model was successfully sliced!")
        return gcode
        
    def write_gcode(self, gcode:str) -> None:
        print("Writing Gcode...")
        gcode_file = open(self.gcode_file_address + ".gcode", 'w')
        gcode_file.write(gcode)
        gcode_file.close()
        print("The Gcode is ready!")