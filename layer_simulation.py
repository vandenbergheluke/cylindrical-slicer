"""
<layer_simulation.py provides a visualization of a layer on the model.>
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

# Imports 
from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 
from PyQt5.QtCore import * 
from PyQt5 import QtCore, QtGui, QtWidgets, uic
import numpy as np
import sys 

class layer_viewer(): 
    def __init__(self, layer_bounds:np.ndarray, radius:float, layer_number:int,
                 location_x:float, location_y:float, location_z:float, 
                 rotation_x:float, rotation_y:float, rotation_z:float): 

        self.layer_bounds = layer_bounds
        self.radius = radius
        self.layer_number = layer_number
        self.location_x = location_x
        self.location_y = location_y
        self.location_z = location_z
        self.rotation_x = rotation_x
        self.rotation_y = rotation_y
        self.rotation_z = rotation_z

        # creating canvas 
        self.image = QImage(1000, 1000, QImage.Format_RGB32) 
  
        # setting canvas color to white 
        self.image.fill(QColor(255, 255, 255)) 
  
        # calling draw_something method 
        self.draw_something() 
        
        #saving image
        self.save()
          
          
    # this method will draw a line 
    def draw_something(self): 
          
        painter = QPainter(self.image) 
         
        # updating it to canvas 
        s = 3
        t_1 = 200
        t_2 = 300
        pen = QtGui.QPen()
        pen.setWidth(3)
        pen.setColor(QtGui.QColor('black'))
        painter.setPen(pen)

        for j in range(0, len(self.layer_bounds)):
            painter.drawLine(
            QtCore.QPoint(self.layer_bounds[j][0] * s + t_1, self.layer_bounds[j][1] * s + t_2), 
            QtCore.QPoint(self.layer_bounds[j][3] * s + t_1, self.layer_bounds[j][4] * s + t_2)
            )
        painter.end()
      
    # save method 
    def save(self): 
          
        # selecting file path 
        filePath =  (f"LAYERS\\layer_{self.layer_number}_" +
                     f"{self.location_x}_{self.location_y}_{self.location_z}_" +
                     f"{self.rotation_x}_{self.rotation_y}_{self.rotation_z}" +
                     ".png")
        fileFormat="PNG"
  
        # saving canvas at desired path 
        self.image.save(filePath, fileFormat)         