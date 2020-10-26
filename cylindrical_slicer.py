"""
<cylindrical_slicer.py cylindrically slices an STL file provided by user.>
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

class cylindrical_slicer:
    def __init__(self, stl_file_address:str, nozzle_diameter:float, 
                 rotation_x:float, rotation_y:float, rotation_z:float, 
                 location_x:float, location_y:float, location_z:float, 
                 cylinder_diameter:float, delta_y:float):
        
        #Upload STL file
        model = mesh.Mesh.from_file(stl_file_address, 'r')
                
        #Error threshold
        self.epsilon = 0.000001
        
        #Triangles that make up the model
        self.triangles = np.float64(model.points)
        num_triangles = len(self.triangles)
        
        #row indices
        self.rows = np.split(np.repeat(np.arange(num_triangles), 3), num_triangles)
        
        #Columns indices
        self.x_columns = np.array([np.arange(0, 9, 3),] * num_triangles)
        self.y_columns = np.array([np.arange(1, 9, 3),] * num_triangles)
        self.z_columns = np.array([np.arange(2, 9, 3),] * num_triangles)
        
        #Center
        self.center_x = np.sum(self.triangles[self.rows, self.x_columns]) / \
                        np.size(self.triangles[self.rows, self.x_columns])
        self.center_y = np.sum(self.triangles[self.rows, self.y_columns]) / \
                        np.size(self.triangles[self.rows, self.y_columns])
        self.center_z = np.sum(self.triangles[self.rows, self.z_columns]) / \
                        np.size(self.triangles[self.rows, self.z_columns])
                        
        #Locations
        self.location_x = location_x
        self.location_y = location_y
        self.location_z = location_z
        
        #Locations
        self.rotation_x = rotation_x
        self.rotation_y = rotation_y
        self.rotation_z = rotation_z
        
        #Rotate model
        self.rotate()
        
        #translate model
        self.translate()
        
        #Get the distance each point is away from the x-axis
        y_squared = np.power(self.triangles[self.rows, self.y_columns], 2)
        z_squared = np.power(self.triangles[self.rows, self.z_columns], 2)
        self.radii = np.sqrt(np.add(y_squared, z_squared))
        self.max_radius = np.amax(self.radii)
        
        #Other parameters
        self.delta_y = delta_y
        self.cylinder_diameter = cylinder_diameter
        self.nozzle_diameter = nozzle_diameter 
        
        #Groups of triangles and radii
        self.tri_case_1 = np.array([])
        self.tri_case_2 = np.array([])
        self.tri_case_3 = np.array([])
        self.tri_case_4 = np.array([])
        self.tri_case_5 = np.array([])
        self.tri_case_6 = np.array([])
        
        self.radii_case_1 = np.array([])
        self.radii_case_2 = np.array([])
        self.radii_case_3 = np.array([])
        self.radii_case_4 = np.array([])
        self.radii_case_5 = np.array([])
        self.radii_case_6 = np.array([])
        
    def rotate(self) -> None: 
        #Convert to radians
        theta_x = self.rotation_x * np.pi / 180
        theta_y = self.rotation_y * np.pi / 180
        theta_z = self.rotation_z * np.pi / 180
        
        #Translate model to origin
        self.triangles[self.rows, self.x_columns] -= self.center_x
        self.triangles[self.rows, self.y_columns] -= self.center_y
        self.triangles[self.rows, self.z_columns] -= self.center_z
        
        #Rotate model x-axis
        y = self.triangles[self.rows, self.y_columns]
        z = self.triangles[self.rows, self.z_columns]      
        self.triangles[self.rows, self.y_columns] = y * np.cos(theta_x) - \
                                                    z * np.sin(theta_x)
        self.triangles[self.rows, self.z_columns] = y * np.sin(theta_x) + \
                                                    z * np.cos(theta_x)
        #Rotate model y-axis
        x = self.triangles[self.rows, self.x_columns]
        z = self.triangles[self.rows, self.z_columns]      
        self.triangles[self.rows, self.x_columns] = x * np.cos(theta_y) + \
                                                    z * np.sin(theta_y)
        self.triangles[self.rows, self.z_columns] = z * np.cos(theta_y) - \
                                                    x * np.sin(theta_y)
        #Rotate model z-axis
        x = self.triangles[self.rows, self.x_columns]
        y = self.triangles[self.rows, self.y_columns]      
        self.triangles[self.rows, self.x_columns] = x * np.cos(theta_z) - \
                                                    y * np.sin(theta_z)
        self.triangles[self.rows, self.y_columns] = x * np.sin(theta_z) + \
                                                    y * np.cos(theta_z)
        
        #Translate model back to original position
        self.triangles[self.rows, self.x_columns] += self.center_x
        self.triangles[self.rows, self.y_columns] += self.center_y
        self.triangles[self.rows, self.z_columns] += self.center_z
    
    def translate(self) -> None:
        self.triangles[self.rows, self.x_columns] += self.location_x
        self.triangles[self.rows, self.y_columns] += self.location_y
        self.triangles[self.rows, self.z_columns] += self.location_z
        
    def sort_triangles(self, r:float) -> None:
        """
        Slicing cylinder with its axis along the x-axis that has a radius "r".
        The cylinder will intersect with a triangle given as
        
        Triangle:
            Vertex 1: distance "r_1" from x-axis
            Vertex 2: distance "r_2" from x-axis
            Vertex 3: distance "r_3" from x-axis
                        
        The triangles of the mesh will first be organized into four seperate 
        groups based on which conditions they satisfy.
        a ∈ {1, 2, 3}, b ∈ {1, 2, 3}, c ∈ {1, 2, 3},  a != b != c
       
        Case 0:
            r >= r_a
            r >= r_b
            r >= r_c
            -possible intersection with triangle vertex omitted
            - intersection with 0 edges 
            - 0 intersection points
        Case 1:
            r < r_a
            r > r_b
            r > r_c
            - intersection with 2 edges 
            - 2 intersection points
        Case 2:
            r < r_a
            r < r_b
            r > r_c
            - intersection with 2 edges 
            - 2 intersection points
            or
            - intersection with 3 edges 
            - 4 intersection points 
            (tangent intersection omitted)
        Case 3:
            r < r_a
            r < r_b
            r < r_c
            - intersection with 0 edges 
            - 0 intersection points
            or
            - intersection with 1 edge 
            - 2 intersection points 
            (tangent intersection omitted)
            or
            - intersection with 2 edges 
            - 4 intersection points 
            (tangent intersection omitted)
            or
            - intersection with 3 edges 
            - 6 intersection points 
            (tangent intersections omitted)
        Case 4:
            r == r_a
            r < r_b
            r < r_c
            - intersection with 2 edges 
            - 2 intersection points 
            (tangent and vertex intersections omitted)
            or
            - intersection with 2 edges 
            - 4 intersection points (vertex included)
            (tangent)
            or
            - intersection with 3 edges 
            - 4 intersection points 
            (tangent and vertex intersections omitted)
            or
            - intersection with 1 edges 
            - 2 intersection points (vertex intersection included)
            (tangent intersections omitted)
        Case 5:
            r == r_a
            r < r_b
            r > r_c
            - intersection with 1 edge 
            - 2 intersection points(vertex intersection included)
            or
            - intersection with 2 edges 
            - 2 intersection points 
            (tangent and vertex intersections omitted)
        Case 6:
            r == r_a
            r == r_b
            r < r_c
            - intersection with 1 edge 
            - 2 intersection points(both vertex intersections included)
            or
            - intersection with 3 edges 
            - 2 intersection points 
            (tangent and vertex intersections omitted)
            or
            - intersection with 2 edges 
            - 2 intersection points (1 vertex included)
            (tangent and vertex intersections omitted)
        """
        #Find the point on each triangle that is furthest from the x-axis
        max_radii = np.array([np.amax(self.radii, axis = 1)])
        #Find the point on each triangle that is in between or equal to the 
        #other two points
        mid_radii = np.array([np.median(self.radii, axis = 1)])
        #Find the point on each triangle that is closest to the x-axis
        min_radii =  np.array([np.amin(self.radii, axis = 1)])

        #greater_than_max = np.where(max_radii < r)
        greater_than_mid = np.where(mid_radii < r)
        greater_than_min = np.where(min_radii < r)
    
        less_than_max = np.where(max_radii > r)
        less_than_mid = np.where(mid_radii > r)
        less_than_min = np.where(min_radii > r)
        
        #equal_to_max = np.where(max_radii == r)
        equal_to_mid = np.where(mid_radii == r)
        equal_to_min = np.where(min_radii == r)
        
        #index_case_0 is not needed
        index_case_1 = np.concatenate((less_than_max[1],
                                       greater_than_mid[1],
                                       greater_than_min[1]), axis=0)
        index_case_2 = np.concatenate((less_than_max[1],
                                       less_than_mid[1],
                                       greater_than_min[1]), axis=0)
        index_case_3 = np.concatenate((less_than_max[1],
                                       less_than_mid[1],
                                       less_than_min[1]), axis=0)
        index_case_4 = np.concatenate((less_than_max[1],
                                       less_than_mid[1],
                                       equal_to_min[1]), axis=0)
        index_case_5 = np.concatenate((less_than_max[1],
                                       greater_than_min[1],
                                       equal_to_mid[1]), axis=0)
        index_case_6 = np.concatenate((less_than_max[1],
                                       equal_to_mid[1],
                                       equal_to_min[1]), axis=0)
        #Group triangles based on case
        cases = (index_case_1, index_case_2, index_case_3, 
                 index_case_4, index_case_5, index_case_6)
        for i in range(len(cases)):
            elements, count = np.unique(cases[i], return_counts = True)
            duplicates = elements[count > 2]
            if i == 0:
                self.tri_case_1 = self.triangles[duplicates, :]
                self.radii_case_1 = self.radii[duplicates, :]
            elif i == 1:
                self.tri_case_2 = self.triangles[duplicates, :]
                self.radii_case_2 = self.radii[duplicates, :]
            elif i == 2:
                self.tri_case_3 = self.triangles[duplicates, :]
                self.radii_case_3 = self.radii[duplicates, :]
            elif i == 3:
                self.tri_case_4 = self.triangles[duplicates, :]
                self.radii_case_4 = self.radii[duplicates, :]
            elif i == 4:
                self.tri_case_5 = self.triangles[duplicates, :]
                self.radii_case_5 = self.radii[duplicates, :]
            elif i == 5:
                self.tri_case_6 = self.triangles[duplicates, :]
                self.radii_case_6 = self.radii[duplicates, :]
    
    def gather_edges(self, r:float) -> np.ndarray:
        #Reset triangle groups and radii groups
        self.tri_case_1 = np.array([])
        self.tri_case_2 = np.array([])
        self.tri_case_3 = np.array([])
        self.tri_case_4 = np.array([])
        self.tri_case_5 = np.array([])
        self.tri_case_6 = np.array([])
        
        self.radii_case_1 = np.array([])
        self.radii_case_2 = np.array([])
        self.radii_case_3 = np.array([])
        self.radii_case_4 = np.array([])
        self.radii_case_5 = np.array([])
        self.radii_case_6 = np.array([])
        
        #Sort triangles into groups
        self.sort_triangles(r)
        
        """
        print("case:1", self.tri_case_1)
        print(self.radii_case_1)
        print("case:2", self.tri_case_2)
        print(self.radii_case_2)
        print("case:3", self.tri_case_3)
        print(self.radii_case_3)
        print("case:4", self.tri_case_4)
        print(self.radii_case_4)
        print("case:5", self.tri_case_5)
        print(self.radii_case_5)
        print("case:6", self.tri_case_6)
        print(self.radii_case_6)
        """
        
        first_case = True
        if len(self.tri_case_1) != 0:
            edges_case_1 = self.case_1(r)
            edges = edges_case_1
            first_case = False
            
        if len(self.tri_case_2) != 0:
            edges_case_2 = self.case_2(r)
            if not(first_case):
                edges = np.append(edges, edges_case_2, axis = 0)
            else:
                edges = edges_case_2
                first_case = False    
                
        if len(self.tri_case_3) != 0:
            edges_case_3 = self.case_3(r)
            if len(edges_case_3) != 0:
                if not(first_case):
                    edges = np.append(edges, edges_case_3, axis = 0)
                else:
                    edges = edges_case_3
                    first_case = False    
                
        if len(self.tri_case_4) != 0:
            edges_case_4 = self.case_4(r)
            if len(edges_case_4) != 0:
                if not(first_case):
                    edges = np.append(edges, edges_case_4, axis = 0)
                else:
                    edges = edges_case_4
                    first_case = False    
                
        if len(self.tri_case_5) != 0:
            edges_case_5 = self.case_5(r)
            if len(edges_case_5) != 0:
                if not(first_case):
                    edges = np.append(edges, edges_case_5, axis = 0)
                else:
                    edges = edges_case_5
                    first_case = False    
                
        if len(self.tri_case_6) != 0:
            edges_case_6 = self.case_6(r)
            if len(edges_case_6) != 0:
                if not(first_case):
                    edges = np.append(edges, edges_case_6, axis = 0)
                else:
                    edges = edges_case_6
                    first_case = False  
        if first_case:
            return "error"
        else:
            edges = self.reconstruct_edges(r, edges)
            return edges
    
    def case_1(self, r:float) -> np.ndarray:
        #print("case 1")
        for i in range(len(self.tri_case_1)):
            r_1 = self.radii_case_1[i][0]
            r_2 = self.radii_case_1[i][1]
            r_3 = self.radii_case_1[i][2]
            if (r_1 < r > r_2):
                edge_1 = np.append(self.tri_case_1[i][3:6], 
                                  self.tri_case_1[i][6:])
                edge_2 = np.append(self.tri_case_1[i][:3], 
                                  self.tri_case_1[i][6:])
            elif (r_2 < r > r_3):
                edge_1 = np.append(self.tri_case_1[i][6:], 
                                  self.tri_case_1[i][:3])
                edge_2 = np.append(self.tri_case_1[i][3:6], 
                                  self.tri_case_1[i][:3])
            elif (r_1 < r > r_3):
                edge_1 = np.append(self.tri_case_1[i][:3], 
                                  self.tri_case_1[i][3:6])
                edge_2 = np.append(self.tri_case_1[i][6:], 
                                  self.tri_case_1[i][3:6])            
            
            point_a, point_b = self.find_intersection(r, edge_1)
            point_c, point_d = self.find_intersection(r, edge_2)
            
            if len(point_a) != 0:
                point_1 = point_a
            else:
                point_1 = point_b
            if len(point_c) != 0:
                point_2 = point_c
            else:
                point_2 = point_d
                
            form_edge = np.append(point_1, point_2)
            unwrapped_edge = self.unwrap(r, form_edge)
            
            if i == 0:
                edges = np.array([unwrapped_edge])   
            else:
                edges = np.append(edges, np.array([unwrapped_edge]), axis = 0)
        return edges
            
    def case_2(self, r:float) -> np.ndarray:
        #print("case 2")
        for i in range(len(self.tri_case_2)):
            r_1 = self.radii_case_2[i][0]
            r_2 = self.radii_case_2[i][1]
            r_3 = self.radii_case_2[i][2]
            if r > r_1:
                opposite_edge = np.append(self.tri_case_2[i][3:6], 
                                          self.tri_case_2[i][6:])
                edge_1 = np.append(self.tri_case_2[i][:3], 
                                  self.tri_case_2[i][3:6])
                edge_2 = np.append(self.tri_case_2[i][:3], 
                                  self.tri_case_2[i][6:])          
            elif r > r_2 :
                opposite_edge = np.append(self.tri_case_2[i][:3], 
                                          self.tri_case_2[i][6:])
                edge_1 = np.append(self.tri_case_2[i][:3], 
                                  self.tri_case_2[i][3:6])
                edge_2 = np.append(self.tri_case_2[i][6:], 
                                  self.tri_case_2[i][3:6])        
            elif r > r_3:
                opposite_edge = np.append(self.tri_case_2[i][:3], 
                                          self.tri_case_2[i][3:6])
                edge_1 = np.append(self.tri_case_2[i][3:6], 
                                  self.tri_case_2[i][6:])
                edge_2 = np.append(self.tri_case_2[i][:3], 
                                  self.tri_case_2[i][6:])
                
            d = self.shortest_distance(opposite_edge)
            
            if r < d or d == 0:
                #print("case 2.1")
                point_a, point_b = self.find_intersection(r, edge_1)
                point_c, point_d = self.find_intersection(r, edge_2)
                if len(point_a) != 0:
                    point_1 = point_a
                else:
                    point_1 = point_b
                if len(point_c) != 0:
                    point_2 = point_c
                else:
                    point_2 = point_d
                    
                form_edge = np.append(point_1, point_2)
                unwrapped_edge = self.unwrap(r, form_edge)
                
                if i == 0:
                    edges = np.array([unwrapped_edge])   
                else:
                    edges = np.append(edges, np.array([unwrapped_edge]), axis = 0)
            
            elif r > d != 0: 
                #print("case 2.2")
                point_a, point_b = self.find_intersection(r, edge_1)
                point_c, point_d = self.find_intersection(r, edge_2)
                point_e, point_f = self.find_intersection(r, opposite_edge)

                if len(point_a) != 0:
                    point_1 = point_a
                else:
                    point_1 = point_b
                if len(point_c) != 0:
                    point_2 = point_c
                else:
                    point_2 = point_d
                
                l_1e = self.point_distance(point_1, point_e)
                l_1f = self.point_distance(point_1, point_f)
                
                l_2e = self.point_distance(point_2, point_e)
                l_2f = self.point_distance(point_2, point_f)
                
                if l_1e < l_1f:
                    if l_1e < l_2e:
                        form_edge_1 = np.append(point_1, point_e)
                        form_edge_2 = np.append(point_2, point_f)
                    else:
                        form_edge_1 = np.append(point_1, point_f)
                        form_edge_2 = np.append(point_2, point_e)
                else:
                    if l_1f < l_2f:
                        form_edge_1 = np.append(point_1, point_f)
                        form_edge_2 = np.append(point_2, point_e)
                    else:
                        form_edge_1 = np.append(point_1, point_e)
                        form_edge_2 = np.append(point_2, point_f)
                
                unwrapped_edge_1 = self.unwrap(r, form_edge_1)
                unwrapped_edge_2 = self.unwrap(r, form_edge_2)
                
                if i != 0:
                    edges = np.append(edges, np.array([unwrapped_edge_1]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                else:
                    edges = np.array([unwrapped_edge_1])
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
        return edges
    
    def case_3(self, r:float) -> np.ndarray:
        #print("case 3")
        first_pass = True
        for i in range(len(self.tri_case_3)):
            edge_1 = np.append(self.tri_case_3[i][3:6], 
                               self.tri_case_3[i][6:])
            edge_2 = np.append(self.tri_case_3[i][:3], 
                               self.tri_case_3[i][3:6])
            edge_3 = np.append(self.tri_case_3[i][:3], 
                               self.tri_case_3[i][6:])      
            d_1 = self.shortest_distance(edge_1)
            d_2 = self.shortest_distance(edge_2)
            d_3 = self.shortest_distance(edge_3)
            
            triangle_edges = np.array([edge_1, edge_2, edge_3])
            distances = np.array([d_1, d_2, d_3])
            
            greater_than_zero = np.where(distances > self.epsilon)
            less_than_radius = np.where(distances < r)
            
            index = np.concatenate((greater_than_zero[0],
                                    less_than_radius[0]), axis=0)
            
            elements, count = np.unique(index, return_counts = True)
            duplicates = elements[count > 1]
            if len(duplicates) == 0:
                #print("case 3.1")
                continue
            
            elif len(duplicates) == 1:
                #print("case 3.2")
                intersecting_edge = triangle_edges[duplicates[0]]
                point_1, point_2 = self.find_intersection(r, intersecting_edge)
                form_edge = np.append(point_1, point_2)
                unwrapped_edge = self.unwrap(r, form_edge)
                
                if first_pass:
                    edges = np.array([unwrapped_edge])
                    first_pass = False
                else:
                    edges = np.append(edges, np.array([unwrapped_edge]), axis = 0)
                    
                    
            elif len(duplicates) == 2:
                #print("case 3.3")
                intersecting_edge_1 = triangle_edges[duplicates[0]]
                intersecting_edge_2 = triangle_edges[duplicates[1]]
                
                point_a, point_b = self.find_intersection(r, intersecting_edge_1)
                point_c, point_d = self.find_intersection(r, intersecting_edge_2)
                
                l_ac = self.point_distance(point_a, point_c)
                l_ad = self.point_distance(point_a, point_d)
                
                l_bc = self.point_distance(point_b, point_c)
                l_bd = self.point_distance(point_b, point_d)
                
                if l_ac < l_ad:
                    if l_ac < l_bc:
                        form_edge_1 = np.append(point_a, point_c)
                        form_edge_2 = np.append(point_b, point_d)
                    else:
                        form_edge_1 = np.append(point_a, point_d)
                        form_edge_2 = np.append(point_b, point_c)
                else:
                    if l_ad < l_bd:
                        form_edge_1 = np.append(point_a, point_d)
                        form_edge_2 = np.append(point_b, point_c)
                    else:
                        form_edge_1 = np.append(point_a, point_c)
                        form_edge_2 = np.append(point_b, point_d)
                
                unwrapped_edge_1 = self.unwrap(r, form_edge_1)
                unwrapped_edge_2 = self.unwrap(r, form_edge_2)
                
                if not(first_pass):
                    edges = np.append(edges, np.array([unwrapped_edge_1]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                else:
                    edges = np.array([unwrapped_edge_1])
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                    first_pass = False
                    
            elif len(duplicates) == 3:
                #print("case 3.4")
                intersecting_edge_1 = triangle_edges[duplicates[0]]
                intersecting_edge_2 = triangle_edges[duplicates[1]]
                intersecting_edge_3 = triangle_edges[duplicates[2]]
                
                point_a, point_b = self.find_intersection(r, intersecting_edge_1)
                point_c, point_d = self.find_intersection(r, intersecting_edge_2)
                point_e, point_f = self.find_intersection(r, intersecting_edge_3)
                
                l_ac = self.point_distance(point_a, point_c)
                l_ad = self.point_distance(point_a, point_d)
                l_ae = self.point_distance(point_a, point_e)
                l_af = self.point_distance(point_a, point_f)
                
                l_bc = self.point_distance(point_b, point_c)
                l_bd = self.point_distance(point_b, point_d)
                l_be = self.point_distance(point_b, point_e)
                l_bf = self.point_distance(point_b, point_f)
                
                if l_ac < l_ad:
                    if l_ac < l_bc:
                        form_edge_1 = np.append(point_a, point_c)
                        if l_be < l_bf:
                            form_edge_2  = np.append(point_b, point_e)
                            form_edge_3  = np.append(point_f, point_d)
                        else:
                            form_edge_2  = np.append(point_b, point_f)
                            form_edge_3  = np.append(point_e, point_d)
                    else:
                        form_edge_1 = np.append(point_b, point_c)
                        if l_ae < l_af:
                            form_edge_2  = np.append(point_a, point_e)
                            form_edge_3  = np.append(point_f, point_d)
                        else:
                            form_edge_2  = np.append(point_a, point_f)
                            form_edge_3  = np.append(point_e, point_d)
                else:
                    if l_ad < l_bd:
                        form_edge_1 = np.append(point_a, point_d)
                        if l_be < l_bf:
                            form_edge_2  = np.append(point_b, point_e)
                            form_edge_3  = np.append(point_f, point_c)
                        else:
                            form_edge_2  = np.append(point_b, point_f)
                            form_edge_3  = np.append(point_e, point_c)
                    else:
                        form_edge_1 = np.append(point_b, point_d)
                        if l_ae < l_af:
                            form_edge_2  = np.append(point_a, point_e)
                            form_edge_3  = np.append(point_f, point_c)
                        else:
                            form_edge_2  = np.append(point_a, point_f)
                            form_edge_3  = np.append(point_e, point_c)
                            
                unwrapped_edge_1 = self.unwrap(r, form_edge_1)
                unwrapped_edge_2 = self.unwrap(r, form_edge_2)
                unwrapped_edge_3 = self.unwrap(r, form_edge_3)
                if not(first_pass):

                    edges = np.append(edges, np.array([unwrapped_edge_1]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_3]), 
                                      axis = 0)
                
                else:
                    edges = np.array([unwrapped_edge_1])
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_3]), 
                                      axis = 0)
                    first_pass = False
        if first_pass:
            edges = np.array([])
        return edges
    
    def case_4(self, r:float) -> np.ndarray:
        #print("case 4")
        first_pass = True
        for i in range(len(self.tri_case_4)):
            edge_1 = np.append(self.tri_case_4[i][3:6], 
                               self.tri_case_4[i][6:])
            edge_2 = np.append(self.tri_case_4[i][:3], 
                               self.tri_case_4[i][3:6])
            edge_3 = np.append(self.tri_case_4[i][:3], 
                               self.tri_case_4[i][6:])      
            d_1 = self.shortest_distance(edge_1)
            d_2 = self.shortest_distance(edge_2)
            d_3 = self.shortest_distance(edge_3)
            
            triangle_edges = np.array([edge_1, edge_2, edge_3])
            distances = np.array([d_1, d_2, d_3])
            greater_than_zero = np.where(distances > self.epsilon)
            less_than_radius = np.where(distances < r)
            
            index = np.concatenate((greater_than_zero[0],
                                    less_than_radius[0]), axis=0)
            
            elements, count = np.unique(index, return_counts = True)
            duplicates = elements[count > 1]
            if len(duplicates) == 0:
                #print("case 4.1")
                continue
            
            elif len(duplicates) == 1:
                #print("case 4.2")
                intersecting_edge = triangle_edges[duplicates[0]]
                point_1, point_2 = self.find_intersection(r, intersecting_edge)
                form_edge = np.append(point_1, point_2)
                unwrapped_edge = self.unwrap(r, form_edge)
                
                if first_pass:
                    edges = np.array([unwrapped_edge])
                    first_pass = False
                else:
                    edges = np.append(edges, np.array([unwrapped_edge]), axis = 0)
                    
            elif len(duplicates) == 2:
                #print("case 4.3")
                intersecting_edge_1 = triangle_edges[duplicates[0]]
                intersecting_edge_2 = triangle_edges[duplicates[1]]
                point_a, point_b = self.find_intersection(r, intersecting_edge_1)
                point_c, point_d = self.find_intersection(r, intersecting_edge_2)
                
                points = np.array([point_a, point_b, point_c, point_d])
                for point in points:
                    difference = np.round(abs(points - point), 8)
                    index = np.where(np.sum(difference, axis=1) < self.epsilon)
                    if len(index[0]) == 2:
                        points = np.delete(points, index, axis=0)
                        break
                if len(points) != 4:
                    form_edge = np.append(points[0], points[1])
                    unwrapped_edge = self.unwrap(r, form_edge)
                    if not(first_pass):
                        edges = np.append(edges, np.array([unwrapped_edge]), 
                                          axis = 0)
                    else:
                        edges = np.array([unwrapped_edge])
                        first_pass = False
                else:
                    l_ac = self.point_distance(point_a, point_c)
                    l_ad = self.point_distance(point_a, point_d)
                    
                    l_bc = self.point_distance(point_b, point_c)
                    l_bd = self.point_distance(point_b, point_d)
                    
                    if l_ac < l_ad:
                        if l_ac < l_bc:
                            form_edge_1 = np.append(point_a, point_c)
                            form_edge_2 = np.append(point_b, point_d)
                        else:
                            form_edge_1 = np.append(point_a, point_d)
                            form_edge_2 = np.append(point_b, point_c)
                    else:
                        if l_ad < l_bd:
                            form_edge_1 = np.append(point_a, point_d)
                            form_edge_2 = np.append(point_b, point_c)
                        else:
                            form_edge_1 = np.append(point_a, point_c)
                            form_edge_2 = np.append(point_b, point_d)
                    
                    unwrapped_edge_1 = self.unwrap(r, form_edge_1)
                    unwrapped_edge_2 = self.unwrap(r, form_edge_2)
                    if not(first_pass):
                        edges = np.append(edges, np.array([unwrapped_edge_1]), 
                                          axis = 0)
                        edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                          axis = 0)
                    else:
                        edges = np.array([unwrapped_edge_1])
                        edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                          axis = 0)
                        first_pass = False
                    
            elif len(duplicates) == 3:
                #print("case 4.4")
                intersecting_edge_1 = triangle_edges[duplicates[0]]
                intersecting_edge_2 = triangle_edges[duplicates[1]]
                intersecting_edge_3 = triangle_edges[duplicates[2]]
                point_a, point_b = self.find_intersection(r, intersecting_edge_1)
                point_c, point_d = self.find_intersection(r, intersecting_edge_2)
                point_e, point_f = self.find_intersection(r, intersecting_edge_3)
                
                points = np.array([point_a, point_b, 
                                   point_c, point_d,
                                   point_e, point_f])
                for point in points:
                    difference = np.round(abs(points - point), 8)
                    index = np.where(np.sum(difference, axis=1) < self.epsilon)
                    if len(index[0]) == 2:
                        points = np.delete(points, index, axis=0)
                        break
                point_a, point_b = points[0], points[1]
                point_c, point_d = points[2], points[3]
                
                l_ac = self.point_distance(point_a, point_c)
                l_ad = self.point_distance(point_a, point_d)
                
                l_bc = self.point_distance(point_b, point_c)
                l_bd = self.point_distance(point_b, point_d)
                
                if l_ac < l_ad:
                    if l_ac < l_bc:
                        form_edge_1 = np.append(point_a, point_c)
                        form_edge_2 = np.append(point_b, point_d)
                    else:
                        form_edge_1 = np.append(point_a, point_d)
                        form_edge_2 = np.append(point_b, point_c)
                else:
                    if l_ad < l_bd:
                        form_edge_1 = np.append(point_a, point_d)
                        form_edge_2 = np.append(point_b, point_c)
                    else:
                        form_edge_1 = np.append(point_a, point_c)
                        form_edge_2 = np.append(point_b, point_d)
                
                unwrapped_edge_1 = self.unwrap(r, form_edge_1)
                unwrapped_edge_2 = self.unwrap(r, form_edge_2)
                
                if not(first_pass):
                    edges = np.append(edges, np.array([unwrapped_edge_1]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                else:
                    edges = np.array([unwrapped_edge_1])
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                    first_pass = False
        if first_pass:
            edges = np.array([])
        return edges
    
    def case_5(self, r:float) -> np.ndarray:
        #print("case 5")
        first_pass = True
        for i in range(len(self.tri_case_5)):
            r_1 = self.radii_case_5[i][0]
            r_2 = self.radii_case_5[i][1]
            r_3 = self.radii_case_5[i][2]
            radii = np.array([r_1, r_2, r_3])
            r_max = np.amax(radii)
            r_min = np.amin(radii)
            
            index_max = int(np.where(abs(r_max - radii) < self.epsilon)[0] + 1) * 3
            index_min = int(np.where(abs(r_min - radii) < self.epsilon)[0] + 1) * 3
            if max(index_max, index_min) == 9:
                index_mid = abs(index_max - index_min)
            else:
                index_mid = abs(index_max + index_min)
            edge_1 = np.append(self.tri_case_5[i][(index_max - 3):index_max], 
                               self.tri_case_5[i][(index_min - 3):index_min])
            edge_2 = np.append(self.tri_case_5[i][(index_max - 3):index_max], 
                               self.tri_case_5[i][(index_mid - 3):index_mid])
            
            vertex_on_circle = self.tri_case_5[i][(index_mid - 3):index_mid]
            
            point_a, point_b = self.find_intersection(r, edge_1)
            if len(point_a) == 0:
                point_1 = point_b
            else:
                point_1 = point_a
                
            distance = self.shortest_distance(edge_2)
            if distance != 0 and distance < r:
                #print("case 5.1")
                point_c, point_d = self.find_intersection(r, edge_2)
                sum_difference_c = sum(abs(point_c - vertex_on_circle))
                sum_difference_d = sum(abs(point_d - vertex_on_circle))
                if sum_difference_c < sum_difference_d:
                    point_2 = point_d
                else:
                    point_2 = point_c
                    
            else:
                #print("case 5.2")
                point_2 = vertex_on_circle
                
            form_edge = np.append(point_1, point_2)
            unwrapped_edge = self.unwrap(r, form_edge)
            
            if first_pass:
                    edges = np.array([unwrapped_edge])
                    first_pass = False
            else:
                edges = np.append(edges, np.array([unwrapped_edge]), axis = 0)
                
        if first_pass:
            edges = np.array([])
        return edges
    
    
    def case_6(self, r:float) -> np.ndarray:
        #print("case 6")
        first_pass = True
        for i in range(len(self.tri_case_6)):
            r_1 = self.radii_case_6[i][0]
            r_2 = self.radii_case_6[i][1]
            r_3 = self.radii_case_6[i][2]
            if (r < r_1):
                edge_1 = np.append(self.tri_case_6[i][6:], 
                                  self.tri_case_6[i][:3])
                edge_2 = np.append(self.tri_case_6[i][3:6], 
                                  self.tri_case_6[i][:3])
                edge_on_cylinder = np.append(self.tri_case_6[i][3:6], 
                                             self.tri_case_6[i][6:])
            elif (r < r_2):
                edge_1 = np.append(self.tri_case_6[i][:3], 
                                  self.tri_case_6[i][3:6])
                edge_2 = np.append(self.tri_case_6[i][6:], 
                                  self.tri_case_6[i][3:6])      
                edge_on_cylinder = np.append(self.tri_case_6[i][:3], 
                                             self.tri_case_6[i][6:])
            elif (r < r_3):
                edge_1 = np.append(self.tri_case_6[i][3:6], 
                                  self.tri_case_6[i][6:])
                edge_2 = np.append(self.tri_case_6[i][:3], 
                                  self.tri_case_6[i][6:])
                edge_on_cylinder = np.append(self.tri_case_6[i][3:6], 
                                             self.tri_case_6[i][:3])
                
            d_1 = self.shortest_distance(edge_1)
            d_2 = self.shortest_distance(edge_2)
            
            triangle_edges = np.array([edge_1, edge_2])
            distances = np.array([d_1, d_2])
            greater_than_zero = np.where(distances > self.epsilon)
            less_than_radius = np.where(distances < r)
            
            index = np.concatenate((greater_than_zero[0],
                                    less_than_radius[0]), axis=0)
            
            elements, count = np.unique(index, return_counts = True)
            duplicates = elements[count > 1]
            if len(duplicates) == 0:
                #print("case 6.1")
                intersecting_edge = edge_on_cylinder
                unwrapped_edge = self.unwrap(r, intersecting_edge)
                if first_pass:
                    edges = np.array([unwrapped_edge])
                    first_pass = False
                else:
                    edges = np.append(edges, np.array([unwrapped_edge]), axis = 0)
                
            if len(duplicates) == 1:
                #print("case 6.2")
                intersecting_edge_1 = triangle_edges[duplicates[0]]
                intersecting_edge_2 = edge_on_cylinder
                point_a, point_b = self.find_intersection(r, intersecting_edge_1)
                point_c, point_d = (intersecting_edge_2[:3], intersecting_edge_2[3:])
                
                points = np.array([point_a, point_b, point_c, point_d])
                for point in points:
                    difference = np.round(abs(points - point), 8)
                    index = np.where(np.sum(difference, axis=1) < self.epsilon)
                    if len(index[0]) == 2:
                        points = np.delete(points, index, axis=0)
                        break
                form_edge = np.append(points[0], points[1])
                unwrapped_edge = self.unwrap(r, form_edge)
                if not(first_pass):
                    edges = np.append(edges, np.array([unwrapped_edge]), 
                                      axis = 0)
                else:
                    edges = np.array([unwrapped_edge])
                    first_pass = False
                    
            elif len(duplicates) == 2:
                #print("case 6.3")
                intersecting_edge_1 = triangle_edges[duplicates[0]]
                intersecting_edge_2 = triangle_edges[duplicates[1]]
                
                point_a, point_b = self.find_intersection(r, intersecting_edge_1)
                point_c, point_d = self.find_intersection(r, intersecting_edge_2)
                
                l_ac = self.point_distance(point_a, point_c)
                l_ad = self.point_distance(point_a, point_d)
                
                l_bc = self.point_distance(point_b, point_c)
                l_bd = self.point_distance(point_b, point_d)
                
                if l_ac < l_ad:
                    if l_ac < l_bc:
                        form_edge_1 = np.append(point_a, point_c)
                        form_edge_2 = np.append(point_b, point_d)
                    else:
                        form_edge_1 = np.append(point_a, point_d)
                        form_edge_2 = np.append(point_b, point_c)
                else:
                    if l_ad < l_bd:
                        form_edge_1 = np.append(point_a, point_d)
                        form_edge_2 = np.append(point_b, point_c)
                    else:
                        form_edge_1 = np.append(point_a, point_c)
                        form_edge_2 = np.append(point_b, point_d)
                
                unwrapped_edge_1 = self.unwrap(r, form_edge_1)
                unwrapped_edge_2 = self.unwrap(r, form_edge_2)
                
                if not(first_pass):
                    edges = np.append(edges, np.array([unwrapped_edge_1]), 
                                      axis = 0)
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                else:
                    edges = np.array([unwrapped_edge_1])
                    edges = np.append(edges, np.array([unwrapped_edge_2]), 
                                      axis = 0)
                    first_pass = False
                
        if first_pass:
            edges = np.array([])
        return edges
    
    def reconstruct_edges(self, r:float, edges:np.ndarray) -> np.ndarray:
        first_pass = True
        num_edges = len(edges)
        delete_edges = []
        for i in range(num_edges):
            if (abs(edges[i][1] - edges[i][4]) > (self.delta_y * 0.6)):
                delete_edges += [i]
                edge = np.array([edges[i][:3], edges[i][3:]])
                edge_sorted = sorted(edge, key=lambda y: y[1])
                if first_pass:
                    point_array_start = np.array([edge_sorted[0]])
                    point_array_end = np.array([edge_sorted[1]])
                    first_pass = False
                else:
                    point_array_start = np.append(point_array_start, 
                                                  np.array([edge_sorted[0]]), 
                                                  axis = 0)
                    point_array_end = np.append(point_array_end, 
                                                np.array([edge_sorted[1]]), 
                                                axis = 0)
                    
        if not(first_pass):
            point_array_start = sorted(point_array_start, key=lambda x: x[0])
            point_array_end = sorted(point_array_end, key=lambda x: x[0])
            if len(point_array_start) % 2 != 0:
                return "error"
            else:
                for i in range(0, len(point_array_start), 2):
                    form_edge_start = point_array_start[i]
                    form_edge_end = point_array_end[i]
                    form_edge_start = np.append(form_edge_start, point_array_start[i+1])
                    form_edge_end = np.append(form_edge_end, point_array_end[i+1])
                    edges = np.append(edges, np.array([form_edge_start]), axis = 0)
                    edges = np.append(edges, np.array([form_edge_end]), axis = 0)
            edges = np.delete(edges, tuple(delete_edges), axis=0)
        return edges
    
    def point_distance(self, point_1:np.ndarray, point_2:np.ndarray) -> float:
        """
        Returns magnitude of vector v_12. This is the distance between points
        1 and 2.
        """
        v_12 = np.subtract(point_2, point_1)
        mag_v_12 = np.sqrt(np.sum(np.power(v_12, 2)))
        return mag_v_12
        
    
    def find_intersection(self, r:float, edge:np.ndarray) -> (np.ndarray, np.ndarray):
        """
        Find intersection point:
            Parametric Equations of line in R3:
                x(t) = x_o + v_x*t 
                y(t) = y_o + v_y*t 
                z(t) = z_o + v_z*t
            Equation of cylinder with axis along the x-axis:
                y^2 + z^2 = r^2
            Through substitution:
                (y_o + v_y*t )^2 + (z_o + v_z*t)^2 = r^2
            Quadratic Equation:
                at^2 + bt + c = 0
            Where:
                a = (v_y)^2 + (v_z)^2
                b = 2 * (y_o * v_y + z_o * v_z)
                c = (y_o)^2 + (z_o)^2 - r^2
            For roots t1, t2 find which if they result in points that
            fit within the bounds of the edge. 
        """
        v_o = edge[:3]
        v = np.subtract(edge[:3], edge[3:])
        a = v[1] ** 2 + v[2] ** 2
        b = 2 * (v_o[1] * v[1] + v_o[2] * v[2])
        c = (v_o[1] ** 2) + (v_o[2] ** 2) - (r ** 2) 
        roots = np.roots([a, b, c])
        
        x_1, x_2 = v_o[0] + np.multiply(roots, v[0])
        y_1, y_2 = v_o[1] + np.multiply(roots, v[1])
        z_1, z_2 = v_o[2] + np.multiply(roots, v[2])
        
        x_min = min(edge[0], edge[3])
        x_max = max(edge[0], edge[3])
        y_min = min(edge[1], edge[4])
        y_max = max(edge[1], edge[4])
        z_min = min(edge[2], edge[5])
        z_max = max(edge[2], edge[5])
        
        equal_to_min_x = abs(x_min - x_1) < self.epsilon
        equal_to_max_x = abs(x_max - x_1) < self.epsilon
        equal_to_min_y = abs(y_min - y_1) < self.epsilon
        equal_to_max_y = abs(y_max - y_1) < self.epsilon
        equal_to_min_z = abs(z_min - z_1) < self.epsilon
        equal_to_max_z = abs(z_max - z_1) < self.epsilon
        
        if (x_min < x_1 < x_max or equal_to_min_x or equal_to_max_x)  and \
           (y_min < y_1 < y_max or equal_to_min_y or equal_to_max_y) and \
           (z_min < z_1 < z_max or equal_to_min_z or equal_to_max_z):
            point_1 = np.array([x_1, y_1, z_1])
        else:
            point_1 = np.array([])
        
        equal_to_min_x = abs(x_min - x_2) < self.epsilon
        equal_to_max_x = abs(x_max - x_2) < self.epsilon
        equal_to_min_y = abs(y_min - y_2) < self.epsilon
        equal_to_max_y = abs(y_max - y_2) < self.epsilon
        equal_to_min_z = abs(z_min - z_2) < self.epsilon
        equal_to_max_z = abs(z_max - z_2) < self.epsilon
        
        if (x_min < x_2 < x_max or equal_to_min_x or equal_to_max_x)  and \
           (y_min < y_2 < y_max or equal_to_min_y or equal_to_max_y) and \
           (z_min < z_2 < z_max or equal_to_min_z or equal_to_max_z):
            point_2 = np.array([x_2, y_2, z_2])
        else:
            point_2 = np.array([])
    
        return point_1, point_2
    
    def unwrap(self, r:float, edge:np.ndarray) -> np.ndarray:
        """
        Given the intersection point (x, y, z), and vector in yz-plane 
        V = <a, b>  where:
                            a = y
                            b = z
        Find the angle vector <a, b> makes with positive y-axis:
            if <a, b> in Q1:
                theta = arctan(b/a)
            elif <a, b> in Q2:
                theta = arctan(b/a) + pi
            elif <a, b> in Q3:
                theta = arctan(b/a) + pi
            elif <a, b> in Q4:
                theta = arctan(b/a) + 2 * pi
        Find the arc length:
            s = theta * r
        Scale based on delta_y and the circumference:
            s' = s * (delta_y / (2 * pi * r)) 
        Unwrap to a plane parallel to xy-plane that is translated 
        along the z-axis to [z' = r - cylinder radius] since the
        z-endstop will be level with the surface of the cylinder.
        
        The point will be transformed to point':
                        
                         point' = (x, s', z')
        """
        for i in range(0, 6, 3):
            a = edge[i+1]
            b = edge[i+2] 
            if a != 0:
                if (a > 0) and (b >= 0):
                    theta = np.arctan(b/a)
                elif (a < 0 and b >= 0) or (a < 0 and b < 0):
                    theta = np.arctan(b/a) + np.pi
                else:
                    theta = np.arctan(b/a) + 2 * np.pi
            else:
                if b > 0:
                    theta = np.pi / 2
                else:
                    theta = 3 * np.pi / 2
            
            edge[i+1] = (theta * r) * self.delta_y / (2 * np.pi * r) 
            edge[i+2] = round((r - self.cylinder_diameter / 2), 2)
        return edge
    
    def shortest_distance(self, edge:np.ndarray) -> float:
        """
        Returns shortest distance between edge and x-axis.
        
        This is an optimization problem:
        Parametric Equations of line in R3:
                x(t) = x_o + v_x*t 
                y(t) = y_o + v_y*t 
                z(t) = z_o + v_z*t
        Distance from the x-axis:
                d(t) = sqrt(y(t)^2 + z(t)^2)
        Through substitution:
                d(t) = sqrt((y_o + v_y*t )^2 + (z_o + v_z*t)^2)
        Take the derivative of d with respect to t:
               d'(t) = ((v_y)^2 +(v_z)^2 + v_y * y_o + v_z * z_o) /
                       sqrt((y_o + v_y*t )^2 + (z_o + v_z*t)^2)
        Find the value of t at d'(t) = 0:
                   0 = (((v_y)^2 +(v_z)^2) * t + v_y * y_o + v_z * z_o) /
                       sqrt((y_o + v_y*t )^2 + (z_o + v_z*t)^2)
        The expression for t is:
                   t = -(v_y * y_o + v_z * z_o) / ((v_y)^2 +(v_z)^2)
        Determine if x(t), y(t), z(t) fit within the bounds of the edge. If
        they fit, return the resulting distance d. If they don't fit, return 0.
        """
        
        v_o = edge[:3]
        v = np.subtract(edge[:3], edge[3:])
        if abs(v[1]) < self.epsilon and abs(v[2]) < self.epsilon: 
            return 0
        t = -(v_o[1] * v[1] + v_o[2] * v[2]) / (v[1] ** 2 + v[2] ** 2) 
        
        
        x = v_o[0] + np.multiply(t, v[0])
        y = v_o[1] + np.multiply(t, v[1])
        z = v_o[2] + np.multiply(t, v[2])
        
        x_min = min(edge[0], edge[3])
        x_max = max(edge[0], edge[3])
        y_min = min(edge[1], edge[4])
        y_max = max(edge[1], edge[4])
        z_min = min(edge[2], edge[5])
        z_max = max(edge[2], edge[5])
        
        equal_to_min_x = abs(x_min - x) < self.epsilon
        equal_to_max_x = abs(x_max - x) < self.epsilon
        equal_to_min_y = abs(y_min - y) < self.epsilon
        equal_to_max_y = abs(y_max - y) < self.epsilon
        equal_to_min_z = abs(z_min - z) < self.epsilon
        equal_to_max_z = abs(z_max - z) < self.epsilon
        
        if (x_min < x < x_max or equal_to_min_x or equal_to_max_x)  and \
           (y_min < y < y_max or equal_to_min_y or equal_to_max_y) and \
           (z_min < z < z_max or equal_to_min_z or equal_to_max_z):
            d = np.sqrt(y ** 2 + z ** 2)
        else:
            d = 0    
        return d
    
    def create_loops(self, edges:np.ndarray) -> (list, list):
        """
        Returns two lists of arrays of closed loops that are organized based
        on the type of region the loop encloses
        """
        z = edges[0][2]
        loop_dict = dict()
        loop_num = 1
        failsafe_threshold = 2 * len(edges)
        while len(edges) != 0:
            failsafe_counter = 0
            loop = np.array([[edges[0][0], edges[0][1], z, 
                              edges[0][3], edges[0][4], z]])
            delete_index = [0]
            while not(abs(loop[0][0] - loop[-1][-3]) < self.epsilon) or \
                  not(abs(loop[0][1] - loop[-1][-2]) < self.epsilon):
                #Exit loop if no closed loop can be found
                failsafe_counter += 1
                if failsafe_counter > failsafe_threshold:
                    return "error"
                edges = np.delete(edges, tuple(delete_index), 0)
                delete_index = []
                for i in range(len(edges)):
                    y_3, y_2, y_1 = edges[i][1],\
                                    edges[i][4],\
                                    loop[-1][-2]
                    x_3, x_2, x_1 = edges[i][0],\
                                    edges[i][3],\
                                    loop[-1][-3]
                    if False not in abs(edges[i] - loop[-1]) < self.epsilon:
                        delete_index += [i]
                    elif (abs(x_2 - x_1) < self.epsilon) and \
                         (abs(y_2 - y_1) < self.epsilon):
                        loop = np.append(loop, np.array([[x_2, y_2, z, 
                                                          x_3, y_3, z]]), 
                                                          axis = 0)
                        delete_index += [i]
                    elif (abs(x_3 - x_1) < self.epsilon) and \
                         (abs(y_3 - y_1) < self.epsilon):
                        loop = np.append(loop, np.array([[x_3, y_3, z, 
                                                          x_2, y_2, z]]), 
                                                          axis=0)
                        delete_index += [i]
            loop_dict.update({loop_num: loop})
            loop_num += 1
            edges = np.delete(edges, tuple(delete_index), 0)
        """
        Now that all the loops of the mesh are found the purpose of the
        next portion of the method is to determine which loops enclose the
        inside of the mesh and which loops enclose free space(holes).
        
        For each loop a tuple containing the key for the loop in the 
        loop_dict, the min and max x and y values and the area of the 
        rectangle with edges that pass through the min and max values is
        placed is a list that is ordered based on which loop encloses
        a region with the largest area.
        
        Note: The area is grossly approximated.
        
        loops are sorted into a dictionary starting with the loop
        the largest area. If the min and max x and y values of a loop  
        with a smaller area is in between the min and max x and y values of
        a loop with a larger area, the smaller loop will be grouped with
        the larger loop meaning the smaller loop is inside the larger
        loop. If the loop with the smaller area is not inside
        the loop with the larger area is assigned to a new group. 
        the next loops will now also be compared with the old and new group
        to see if it lies inside a loop.
        """
        for key in loop_dict:
            rows = np.split(np.repeat(np.arange(len(loop_dict[key])),2), 
                                                len(loop_dict[key]))
            x_columns = np.array([np.arange(0, 6, 3),]*len(loop_dict[key]))
            y_columns = np.array([np.arange(1, 6, 3),]*len(loop_dict[key]))
            x_min = np.amin(loop_dict[key][rows, x_columns])
            x_max = np.amax(loop_dict[key][rows, x_columns])
            y_min = np.amin(loop_dict[key][rows, y_columns])
            y_max = np.amax(loop_dict[key][rows, y_columns])
            area = abs((y_max - y_min) * (x_max - x_min))
            if key == 1:
                key_order = [(key, area, x_min, x_max, y_min, y_max)]
            else:
                key_order += [(key, area, x_min, x_max, y_min, y_max)]   
        key_order = sorted(key_order, key=lambda a: a[1], reverse=True)
        key_dict = {1: [key_order[0]]}
        del key_order[0]
        index = []
        counter = 1
        while 0 != len(key_order):
            for i in range(len(key_order)):
                inside_loop = False
                for key in key_dict:
                    x_min_1 = key_dict[key][0][2]
                    x_min_2 = key_order[i][2]
                    x_max_1 = key_dict[key][0][3]
                    x_max_2 = key_order[i][3]
                    if (x_min_1 < x_min_2) and (x_max_1 > x_max_2):
                        y_min_1 = key_dict[key][0][4]
                        y_min_2 = key_order[i][4]
                        y_max_1 = key_dict[key][0][5]
                        y_max_2 = key_order[i][5]
                        if (y_min_1 < y_min_2) and (y_max_1 > y_max_2):
                            key_dict[key].append(key_order[i])
                            inside_loop = True           
                if not(inside_loop):
                    counter += 1
                    key_dict.update({counter: [key_order[i]]})
                index += [i]
            for j in sorted(index, reverse = True):
                del key_order[j]
            index.clear()
        """
        The loops will be organized based on the type of region they enclose.
        The loop enclosing the largest area is always enclosing the inside of
        the mesh. The algorithm will only run if there is more than one loop
        inside the outer loop. The loops are already arranged from least to 
        greatest area. Therefore the second loop must enclose a region that is 
        not the inside of the mesh which is why variable region_free is initially  
        True. The midpoint of the other loops will be calculated and if 
        the midpoint is inside  the enclosed area of the second loop, the variable
        loop_inside will be set to True and the other loop will be
        kept track of. This will be repeated for the third, fourth... loops
        
        If there is a loop inside the outer loop, The inner loop must enclose 
        the opposite region of the outer_loop so the inner loop will be moved to
        the front of the list and the region_free variable is switched
        The outer loop is added to its corresponding list and removed from 
        the dictionary.
        """
        enclosed_region_mesh = []
        enclosed_region_free = []
        counter = 2
        for key in key_dict:
            region_free = True
            loop_inside = False
            loop = loop_dict[key_dict[key][0][0]]
            enclosed_region_mesh += [loop]
            if len(key_dict[key]) > 2:
                del key_dict[key][0]
                while len(key_dict[key]) != 0:
                    loop = loop_dict[key_dict[key][0][0]]
                    for i in range(1, len(key_dict[key])):
                        x_min = key_dict[key][i][2]
                        x_max = key_dict[key][i][3]
                        y_min = key_dict[key][i][4]
                        y_max = key_dict[key][i][5]
                        midpoint = ((x_min + x_max) / 2, (y_min + y_max) / 2)
                        for j in range(len(loop)):
                            y_2, y_1 = (loop[j][1],
                                        loop[j][4]) 
                            x_2, x_1 = (loop[j][0],
                                        loop[j][3])
                            x_mid = midpoint[0]
                            y_mid = midpoint[1]
                            y_min = min(y_2, y_1)
                            y_max = max(y_2, y_1)
                            if (y_max >= y_mid >= y_min):
                                for k in range(len(loop)):
                                    if k != j: 
                                        y_4, y_3 = (loop[k][1],
                                                    loop[k][4]) 
                                        x_4, x_3 = (loop[k][0],
                                                    loop[k][3])
                                        x_min = min(x_4, x_3, x_2, x_1)
                                        x_max = max(x_4, x_3, x_2, x_1)
                                        y_min = min(y_4, y_3)
                                        y_max = max(y_4, y_3)
                                        if (y_max >= y_mid >= y_min):
                                            if (x_max >= x_mid >= x_min): 
                                               loop_inside = True
                                               loop_holder = key_dict[key][i]
                                               loop_index = i
                                               counter += 1
                                               if counter > 2:
                                                   loop_inside = False                            
                    counter = 0
                    if not(loop_inside):
                        if region_free:
                            enclosed_region_free += [loop] 
                        else:
                            enclosed_region_mesh += [loop]
                        del key_dict[key][0]    
                        region_free = True
                    elif loop_inside:
                        if region_free:
                            enclosed_region_free += [loop] 
                        else:
                            enclosed_region_mesh += [loop]
                        
                        key_dict[key][0] = loop_holder
                        del key_dict[key][loop_index]
                        region_free = not(region_free)  
                        loop_inside = False
            elif len(key_dict[key]) == 2:
                loop = loop_dict[key_dict[key][1][0]]
                enclosed_region_free +=  [loop]
        return enclosed_region_mesh, enclosed_region_free
    
    def scale_loops(self, scaling_factor:float, enclosed_region_mesh:list, 
                    enclosed_region_free:list) -> np.ndarray:
        """
        Returns an array of scaled loops that are resized based on the type of 
        region they enclose.
        1 <= scaling_factor < 2
        To maintain the same dimensions while creating the wall lines
        during print, the loops enclosing the inside of the mesh will be 
        scaled down and the loops enclosing a free region will be scaled up.
        """
        for loop in enclosed_region_mesh:
            rows = np.split(np.repeat(np.arange(len(loop)),2), len(loop))
            x_columns = np.array([np.arange(0, 6, 3),]*len(loop))
            y_columns = np.array([np.arange(1, 6, 3),]*len(loop))
            x_translation = np.sum(loop[rows, x_columns]) / \
                            np.size(loop[rows, x_columns])
            y_translation = np.sum(loop[rows, y_columns]) / \
                            np.size(loop[rows, y_columns])
            loop[rows, x_columns] -= x_translation 
            loop[rows, y_columns] -= y_translation
            loop[rows, x_columns] *= (2 - scaling_factor)
            loop[rows, y_columns] *= (2 - scaling_factor)
            loop[rows, x_columns] += x_translation
            loop[rows, y_columns] += y_translation
        
        for loop in enclosed_region_free:
            rows = np.split(np.repeat(np.arange(len(loop)),2), len(loop))
            x_columns = np.array([np.arange(0, 6, 3),]*len(loop))
            y_columns = np.array([np.arange(1, 6, 3),]*len(loop))
            x_translation = np.sum(loop[rows, x_columns]) / \
                            np.size(loop[rows, x_columns])
            y_translation = np.sum(loop[rows, y_columns]) / \
                            np.size(loop[rows, y_columns])
            loop[rows, x_columns] -= x_translation 
            loop[rows, y_columns] -= y_translation
            loop[rows, x_columns] *= scaling_factor
            loop[rows, y_columns] *= scaling_factor
            loop[rows, x_columns] += x_translation 
            loop[rows, y_columns] += y_translation     
 
        first_pass = False
        for i in range(len(enclosed_region_free)):
            for j in range(len(enclosed_region_free[i])):
                scaled_loop = np.array([enclosed_region_free[i][j]])
                if i == 0 and j == 0:
                    scaled_loops = scaled_loop
                    first_pass = True
                else:
                    scaled_loops = np.append(scaled_loops, scaled_loop, axis = 0) 
        for i in range(len(enclosed_region_mesh)):
            for j in range(len(enclosed_region_mesh[i])):
                scaled_loop = np.array([enclosed_region_mesh[i][j]])
                if not(first_pass):
                    scaled_loops = scaled_loop
                    first_pass = True
                else:
                    scaled_loops = np.append(scaled_loops, scaled_loop, axis = 0)            
        return scaled_loops
    
    def infill(self, loops:np.ndarray, orientation:int) -> np.ndarray:
        """
        Returns an array of ordered coordinates that define the 
        tool path of the printer while printing the infill. Only
        100% infill is supported.
        """
        edges = loops        
        rows = np.split(np.repeat(np.arange(len(edges)),2),len(edges))
        x_columns = np.array([np.arange(0, 6, 3),]*len(edges))
        y_columns = np.array([np.arange(1, 6, 3),]*len(edges))
        x_min = np.amin(edges[rows, x_columns])
        x_max = np.amax(edges[rows, x_columns])
        y_min = np.amin(edges[rows, y_columns])
        y_max = np.amax(edges[rows, y_columns])
 
        spacing = self.nozzle_diameter * 1.18 #space between each path
        
        if orientation == 0:#0 degree
            first_pass = True
            num_of_y_increments = int(round((y_max - y_min) / spacing))
            for i in range(1, num_of_y_increments):
                line_bounds = []
                y = y_min + i * spacing
                for j in range(len(edges)):
                    up_bound = max(edges[j][1], edges[j][4])
                    low_bound = min(edges[j][1], edges[j][4])
                    if up_bound >= y >= low_bound:
                        y_2, y_1 = edges[j][1], edges[j][4] 
                        x_2, x_1 = edges[j][0], edges[j][3]
                        z = edges[j][2]
                        if abs(x_2 - x_1) < self.epsilon:
                            x = x_1
                            line_bounds += [(x, y, z)]
                        elif abs(y_2 - y_1) < self.epsilon:
                            line_bounds += [(x_1, y, z), (x_2, y, z)]
                        else:
                            m = (y_2 - y_1)/ (x_2 - x_1)
                            x = (y - y_1) / m + x_1
                            line_bounds += [(x, y, z)]          
                line_bounds = sorted(line_bounds, key=lambda x: x[0])
                if line_bounds != [] and len(line_bounds) != 1:
                    if first_pass:
                        bounds = [line_bounds]
                        first_pass = False
                    else:
                        bounds.append(line_bounds)
                        
        elif orientation == 90: #90 degree 
            first_pass = True
            num_of_x_increments = int(round((x_max - x_min) / spacing))
            for i in range(1, num_of_x_increments):
                line_bounds = []
                x = x_min + i * spacing
                for j in range(len(edges)):
                    up_bound = max(edges[j][0], edges[j][3])
                    low_bound = min(edges[j][0], edges[j][3])
                    if up_bound >= x >= low_bound:
                        y_2, y_1 = edges[j][1], edges[j][4] 
                        x_2, x_1 = edges[j][0], edges[j][3]
                        z = edges[j][2]
                        if abs(x_2 - x_1) < self.epsilon:
                            line_bounds += [(x, y_1, z), (x, y_2, z)]
                        elif abs(y_2 - y_1) < self.epsilon:
                            y = y_1
                            line_bounds += [(x, y, z)]
                        else:
                            m = (y_2 - y_1)/ (x_2 - x_1)
                            y = (x - x_1) * m + y_1
                            line_bounds += [(x, y, z)]          
                line_bounds = sorted(line_bounds, key=lambda x: x[1])
                if line_bounds != [] and len(line_bounds) != 1:
                    if not first_pass:
                        bounds.append(line_bounds)
                    else:
                        bounds = [line_bounds]
                        first_pass = False
                    
        elif orientation == 45: #45 degree
            first_pass = True 
            x_mid = (x_min + x_max) / 2
            y_mid = (y_min + y_max) / 2
            x_squared = np.square(edges[rows, x_columns] - x_mid)
            y_squared = np.square(edges[rows, y_columns] - y_mid)
            radius = np.amax(np.sqrt(x_squared + y_squared))
            x_start = x_mid + radius * np.cos(3 * np.pi/4)
            y_start = y_mid + radius * np.sin(3 * np.pi/4)
            x_end = x_mid + radius * np.cos(-np.pi/4)
            y_end = y_mid + radius * np.sin(-np.pi/4)
            b = y_start - x_start
            b_end = y_end - x_end
            while b > b_end:
                b -= spacing
                line_bounds = []
                for j in range(len(edges)):
                    found_intersection = False
                    up_bound_y = max(edges[j][1], edges[j][4])
                    low_bound_y = min(edges[j][1], edges[j][4])
                    up_bound_x = max(edges[j][0], edges[j][3])
                    low_bound_x = min(edges[j][0], edges[j][3])
                    y_2, y_1 = edges[j][1], edges[j][4] 
                    x_2, x_1 = edges[j][0], edges[j][3]
                    z = edges[j][2]
                    if abs(x_2 - x_1) < self.epsilon:
                        x = x_1
                        y = x + b 
                        intersection = (x, y, z)
                        found_intersection = True
                    elif abs(y_2 - y_1) < self.epsilon:
                        y = y_1
                        x = y - b
                        intersection = (x, y, z)
                        found_intersection = True
                    else:
                        m = (y_2 - y_1)/ (x_2 - x_1)
                        if abs(m - 1) < self.epsilon:
                            continue
                        else:
                            b_1 = y_1 - m * x_1
                            x = (b - b_1) / (m - 1) 
                            y = x + b
                            intersection = (x, y, z)
                            found_intersection = True
                    if found_intersection:
                        found_intersection = False
                        if (low_bound_x <= intersection[0] <= up_bound_x) and \
                           (low_bound_y <= intersection[1] <= up_bound_y):
                            line_bounds += [intersection]
                line_bounds = sorted(line_bounds, key=lambda x: x[0])
                if line_bounds != [] and len(line_bounds) != 1:
                    if first_pass:
                        bounds = [line_bounds]
                        first_pass = False
                    else:
                        bounds.append(line_bounds)
                        
        elif orientation == 135: #135 degrees
            first_pass = True 
            x_mid = (x_min + x_max) / 2
            y_mid = (y_min + y_max) / 2
            x_squared = np.square(edges[rows, x_columns] - x_mid)
            y_squared = np.square(edges[rows, y_columns] - y_mid)
            radius = np.amax(np.sqrt(x_squared + y_squared))
            x_start = x_mid + radius * np.cos(np.pi/4)
            y_start = y_mid + radius * np.sin(np.pi/4)
            x_end = x_mid + radius * np.cos(5 * np.pi/4)
            y_end = y_mid + radius * np.sin(5 * np.pi/4)
            b = y_start + x_start
            b_end = y_end + x_end
            while b > b_end:
                b -= spacing
                line_bounds = []
                for j in range(len(edges)):
                    found_intersection = False
                    up_bound_y = max(edges[j][1], edges[j][4])
                    low_bound_y = min(edges[j][1], edges[j][4])
                    up_bound_x = max(edges[j][0], edges[j][3])
                    low_bound_x = min(edges[j][0], edges[j][3])
                    y_2, y_1 = edges[j][1], edges[j][4] 
                    x_2, x_1 = edges[j][0], edges[j][3]
                    z = edges[j][2]
                    if abs(x_2 - x_1) < self.epsilon:
                        x = x_1
                        y = -x + b 
                        intersection = (x, y, z)
                        found_intersection = True
                    elif abs(y_2 - y_1) < self.epsilon:
                        y = y_1
                        x = -(y - b)
                        intersection = (x, y, z)
                        found_intersection = True
                    else:
                        m = (y_2 - y_1)/ (x_2 - x_1)
                        if abs(m - 1) < self.epsilon:
                            continue
                        else:
                            b_1 = y_1 - m * x_1
                            x = (b - b_1) / (m + 1) 
                            y = -x + b
                            intersection = (x, y, z)
                            found_intersection = True
                    if found_intersection:
                        found_intersection = False
                        if (low_bound_x <= intersection[0] <= up_bound_x) and \
                           (low_bound_y <= intersection[1] <= up_bound_y):
                            line_bounds += [intersection]
                            
                line_bounds = sorted(line_bounds, key=lambda x: x[0])
                if line_bounds != [] and len(line_bounds) != 1:
                    if first_pass:
                        bounds = [line_bounds]
                        first_pass = False
                    else:
                        bounds.append(line_bounds)
        """        
        Each line_bounds must have an even number of points. It follows a 
        pattern where every second interval defines a boundary around a region 
        that does not enclose the inside of the mesh.
        """
        for i in range(len(bounds)- 1, -len(bounds) - 1, -1):
            if len(bounds[i]) > 2:
                for j in range(0, (len(bounds[i]) - 1), 2):
                   bounds += [[bounds[i][j], bounds[i][j+1]]]
                del bounds[i]
        counter = 0
        while len(bounds) != 0:
            if counter == 0:
                ordered_bounds = np.array([[bounds[0][0][0], 
                                            bounds[0][0][1], 
                                            bounds[0][0][2],
                                            bounds[0][1][0], 
                                            bounds[0][1][1], 
                                            bounds[0][1][2]]])
                del bounds[0]
                counter = 1
            else:
                x_o = ordered_bounds[-1][3]
                y_o = ordered_bounds[-1][4]
                for i in range(len(bounds)):
                    x_2, x_1 = bounds[i][1][0], bounds[i][0][0]
                    y_2, y_1 = bounds[i][1][1], bounds[i][0][1]
                    z_2, z_1 = bounds[i][1][2], bounds[i][0][2]
                    l_1 = np.sqrt((x_1-x_o)**2 + (y_1-y_o)**2)
                    l_2 = np.sqrt((x_2-x_o)**2 + (y_2-y_o)**2)
                    if i == 0:
                        if l_2 > l_1:
                            l_min = l_1
                            closest_bounds = np.array([[x_1, y_1, z_1, 
                                                       x_2, y_2, z_2]])
                            index = i
                        else:
                            l_min = l_2
                            closest_bounds = np.array([[x_2, y_2, z_2, 
                                                       x_1, y_1, z_1]])
                            index = i
                    elif l_1 < l_2:
                        if l_min > l_1:
                            l_min = l_1
                            closest_bounds = np.array([[x_1, y_1, z_1, 
                                                       x_2, y_2, z_2]])
                            index = i
                    else:
                        if l_min > l_2:
                            l_min = l_2
                            closest_bounds = np.array([[x_2, y_2, z_2, 
                                                       x_1, y_1, z_1]])
                            index = i
                ordered_bounds = np.append(ordered_bounds, closest_bounds, 
                                                                  axis = 0)
                del bounds[index]
        
        return ordered_bounds