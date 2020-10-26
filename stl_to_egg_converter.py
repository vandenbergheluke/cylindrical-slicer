"""
<stl_to_egg_converter.py is a file converter that converts .stl to .egg>
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
import numpy as np
from stl import mesh

class stl_to_egg:
    def __init__(self, file):
        self.your_mesh = mesh.Mesh.from_file(file, 'r')
        egg_file = open("EGG\model.egg", 'w')
        egg_file.write(self.vertex_data())
        egg_file.write(self.polygon_data())
        egg_file.close()
        
    def vertex_data(self) -> str:
        vertex_pool = "<VertexPool> model {\n"
        vertex_count = 0
        for triangle in self.your_mesh.points:
            for i in range(0, 9, 3):
                brace = "{" 
                vertex_pool += (f"  <Vertex> {vertex_count} {brace}\n" +
                                f"    {triangle[i]} " +
                                f"{triangle[i + 1]} " +
                                f"{triangle[i + 2]}\n" +
                                "  }\n")
                vertex_count += 1
        vertex_pool += "}"
        return vertex_pool
    
    def polygon_data(self) -> str:
        vertex_count = 0
        polygons = ""
        for normal in self.your_mesh.normals:
            brace_1 = "{"
            brace_2 = "}" 
            polygons += (f"<Polygon> {brace_1}\n" +
                            f"    <Normal> {brace_1} {normal[0]} {normal[1]} {normal[2]} {brace_2}\n" +
                            "    <RGBA> { 1 1 1 1 }\n" +
                            f"    <VertexRef> {brace_1} ")
            for i in range(3):
                polygons += f"{vertex_count} "
                vertex_count += 1
            polygons += "<Ref> {model} } \n}\n"
        return polygons