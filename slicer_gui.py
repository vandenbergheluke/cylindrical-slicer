"""
<slicer_gui.py displays the user interface for the slicer.>
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

#Panda Imports
from direct.showbase.ShowBase import ShowBase
from direct.showbase import DirectObject
from panda3d.core import *
from direct.task import Task
from direct.gui.DirectGui import *
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText

#Slicer Imports
import stl_to_egg_converter as stl2egg
import gcode_parser as gp
import layer_simulation as layersim
import cylindrical_slicer as cs
import configuration as config

#Other Imports
from tkinter import *
import tkinter.filedialog
import numpy as np
import threading
import time

confVars = """
win-size 1920 1080
window-title ANGL3D PRINTING - Cylindrical Slicer 0.1.0-alpha
"""

loadPrcFileData("", confVars)

class slicer_gui (ShowBase):
    def __init__(self):
        super().__init__()
        #Default Values
        #User input values
        self.stl_file_address = ""
        self.layer_height = config.layer_height
        self.print_speed = config.print_speed
        self.infill_percentage = config.infill_percentage
        self.print_temperature = config.print_temperature
        self.retraction_length = config.retraction_length
        self.retraction_speed = config.retraction_speed
        self.nozzle_diameter = config.nozzle_diameter
        self.wall_line_count = config.wall_line_count
        self.start_gcode = config.start_gcode
        self.end_gcode = config.end_gcode
        self.flavor = config.flavor
        self.header = config.header
        self.location_x = config.location_x
        self.location_y = config.location_y
        self.location_z = config.location_z
        self.rotation_x = config.rotation_x
        self.rotation_y = config.rotation_y
        self.rotation_z = config.rotation_z
        self.cylinder_diameter = config.cylinder_diameter
        self.cylinder_length = config.cylinder_length
        self.delta_y = config.delta_y
        self.filament_diameter = config.filament_diameter
        self.infill_orientation = config.infill_orientation

        #Background Color
        base.setBackgroundColor(0.1, 0.1, 0.1)
        
        #Logo placed at the center of the screen
        self.logo = OnscreenImage(image = r"\GRAPHICS\logo_start_screen.png",
                                  pos = (0, 0, 0.7), 
                                  scale = (0.65, 0.2, 0.2))
        self.logo.setTransparency(TransparencyAttrib.MAlpha)
        
        #Set the font
        self.font = self.loader.loadFont(r"\FONT\Audiowide-Regular.ttf")
        
        #Display the upload STL Button
        self.upload_stl = DirectButton(image = (r"\GRAPHICS\button_unselect.png", 
                                                r"\GRAPHICS\button_select.png",
                                                r"\GRAPHICS\button_select.png", 
                                                r"\GRAPHICS\button_select.png"),
                                       relief = None, 
                                       scale = (0.19, 0.12, 0.05), 
                                       command = self.uploadStlButton,
                                       pos = (0, 0, -0.8))
        self.upload_stl.setTransparency(TransparencyAttrib.MAlpha)
        self.upload_stl.resetFrameSize()
        
        #Display STL upload button text
        self.upload_stl_label = TextNode('Text')
        self.upload_stl_label.setText("Upload File") 
        node = aspect2d.attachNewNode(self.upload_stl_label)
        self.upload_stl_label_NodePath = node
        self.upload_stl_label_NodePath.setScale(0.05)
        self.upload_stl_label.setFont(self.font)
        self.upload_stl_label_NodePath.setPos(-0.15, 0, -0.81)
        
        #Show cylinder
        self.cylinder = self.loader.loadModel(r"\EGG\cylinder.egg")
        self.cylinder.setColorScale(1, 1, 1, 1)
        self.cylinder.setPos(0, 0, 0)
        self.cylinder.setHpr(0, 0, 0)
        self.cylinder.setScale(self.cylinder_length, 
                               self.cylinder_diameter, 
                               self.cylinder_diameter)
        self.cylinder.reparentTo(self.render)
        self.cam.lookAt(self.cylinder)
        
        #STL origin
        self.origin_x = -self.cylinder_length / 2
        self.origin_y = 0
        self.origin_z = 0
        
        #STL original orientation
        self.original_rotation_x = 0
        self.original_rotation_y = 0
        self.original_rotation_z = 0
        
        #starting layer
        self.layer_number = 1
        
        #disables default mouse control
        self.disableMouse()
        # Define camera parameters
        ## Camera angles
        self.camHorAng = 40
        self.camVerAng = 30
        self.camLens.setFov(self.camHorAng, self.camVerAng)
        ## Near/Far plane
        self.camNear = 1    
        self.camLens.setNear(self.camNear)
        self.camFar = 10000
        self.camLens.setFar(self.camFar)
        ## Camera pivot
        self.camPivot = self.render.attach_new_node("cam_pivot")
        self.cam.reparent_to(self.camPivot)
        self.cam.set_y(-100.)
        ## Camera step for changes
        self.camSpeed = .05
        self.camZoomStep = 100
        
        #set position of camera
        self.cam_pos_x = 0
        self.cam_pos_y = -700
        self.cam_pos_z = 0
        self.cam.setPos(self.cam_pos_x,self.cam_pos_y, self.cam_pos_z)
        pivot = self.camPivot
        pivot.set_hpr(10, -10, 0.)
        
        # Set up camera zoom
        self.accept('wheel_up', self.zoom_in)
        self.accept('wheel_down', self.zoom_out)
        
        # Set up camera rotation    
        self.accept('mouse2', self.wheel_down)
        self.accept('mouse2-up', self.wheel_up)
        self.lastMousePos = None
        self.wheel_pressed = False
        self.taskMgr.add(self.rotate_view, 'Rotate Camera View')
        
        #Activate lighting
        self.lighting()
        
    def zoom_out(self) -> None:
        #Translate the camera along its local y axis to zoom out the view
        self.view_changed = True
        self.cam.set_y(self.cam, -self.camZoomStep)

    def zoom_in(self) -> None:
        #Translate the camera along its local y axis to zoom in the view
        self.view_changed = True
        self.cam.set_y(self.cam, self.camZoomStep)
        
    # methods for camera rotation
    def wheel_down(self) -> None:
        self.wheel_pressed = True
        self.lastMousePos = None

    def wheel_up(self) -> None:
        self.wheel_pressed = False
        self.lastMousePos = None
        
    def rotate_view(self, task):
        if self.wheel_pressed and self.mouseWatcherNode.hasMouse():
            mouse_pos = self.mouseWatcherNode.getMouse()
            if self.lastMousePos is None:
                self.lastMousePos = Point2(mouse_pos)
            else:
                d_heading, d_pitch = (mouse_pos - self.lastMousePos) * 100.
                pivot = self.camPivot
                pivot.set_hpr(pivot.get_h() - d_heading, 
                              pivot.get_p() + d_pitch, 0.)
                self.view_changed = True
                self.lastMousePos = Point2(mouse_pos)
        return task.again
        
    def lighting(self) -> None:
        #Set up lighting        
        plight_1 = PointLight("plight")
        plight_1.setColor((1, 1, 1, 1))
        plnp_1 = self.render.attachNewNode(plight_1)
        plnp_1.setPos(100, 100 , -100)
        self.render.setLight(plnp_1)
        
        plight_2 = PointLight("plight")
        plight_2.setColor((1, 1, 1, 1))
        plnp_2 = self.render.attachNewNode(plight_2)
        plnp_2.setPos(100, 100, 100)
        self.render.setLight(plnp_2)
        
        plight_3 = PointLight("plight")
        plight_3.setColor((1, 1, 1, 1))
        plnp_3 = self.render.attachNewNode(plight_3)
        plnp_3.setPos(600, 600 , 0)
        self.render.setLight(plnp_3)
        
        plight_4 = PointLight("plight")
        plight_4.setColor((1, 1, 1, 1))
        plnp_4 = self.render.attachNewNode(plight_4)
        plnp_4.setPos(-600, -600 , 0)
        self.render.setLight(plnp_4)
        
        plight_5 = PointLight("plight")
        plight_5.setColor((1, 1, 1, 1))
        plnp_5 = self.render.attachNewNode(plight_5)
        plnp_5.setPos(0, -50 , 20)
        self.render.setLight(plnp_5)
        
    def uploadStlButton(self) -> None:
        root = Tk()
        root.withdraw()
        self.path = tkinter.filedialog.askopenfilename()
        root.destroy()
        if len(self.path) != 0:
            self.loading_label = TextNode('Text')
            self.loading_label.setText("Loading File...") 
            self.loading_label_NodePath = aspect2d.attachNewNode(self.loading_label)
            self.loading_label_NodePath.setScale(0.05)
            self.loading_label.setFont(self.font)
            self.loading_label_NodePath.setPos(-0.2,0, -0.55)
            t1 = threading.Thread(target = self.uploadStl)
            t1.start()
            cm = CardMaker("c")
            cm.setFrame(-100, 100, -100, 100)
            cn = pixel2d.attachNewNode(cm.generate())
            cn.setPos(950, 0, -750)
           
            vertex = """
            #version 150
            uniform mat4 p3d_ModelViewProjectionMatrix;
            uniform mat4 trans_model_to_world;
            in vec4 p3d_Vertex;
            in vec2 p3d_MultiTexCoord0;
            out vec2 texcoord;
            void main() {
                gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
                texcoord = (p3d_Vertex).xz;
            }
            """
            
            fragment = """
            #version 150
            out vec4 color;
            in vec2 texcoord;
            uniform float radiusStart;
            uniform float radiusEnd;
            uniform vec3 circleColor;
            uniform float progress;
            
            const float PI = 3.14159265359;
            void main() {
                float radius = distance(texcoord, vec2(0));
                color = vec4(0);
                if (radius > radiusStart && radius < radiusEnd) {
                   float angle = atan(texcoord.x, texcoord.y) / (2.0*PI);
                   if (angle < 0.0) angle = 1.0 + angle;
                   if (angle < progress) {
                       // Uncomment this to get a gradient
                       //color = vec4(angle*circleColor, 1);    
                       color = vec4(circleColor, 1);    
                   }
               }
            }
            """
           
            cn.setShader(Shader.make(Shader.SLGLSL, vertex, fragment))
            cn.setShaderInput("radiusStart", 30.0)
            cn.setShaderInput("radiusEnd", 35)
            counter_1 =0
            counter_2 = 0
            while not self.done:
                counter_1 += 1
                if counter_1 > 100:
                    if counter_2 == 100:
                        counter_1 = 0
                        counter_2 = 0
                    counter_2 += 1
                    cn.setShaderInput("circleColor", Vec3(1, 1, 1))
                    cn.setShaderInput("progress", counter_2 * 0.01)
                    cn.setTransparency(True)
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame()
                    time.sleep(0.01)
                else:
                    cn.setShaderInput("circleColor", Vec3(1, 1, 1))
                    cn.setShaderInput("progress", counter_1 * 0.01)
                    cn.setTransparency(True)
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame()
                    time.sleep(0.01)
            self.loading_label.setText("")
            cn.setPos(950, 0, 100000)
            

    def uploadStl(self) -> None:
        
        self.done = False
        #Converting the stl file to egg file so it can be viewed in slicer
        stl2egg.stl_to_egg(self.path)
        
        #store file address
        self.stl_file_address = self.path
        
        #Load STL file
        self.stl = self.loader.loadModel(r"\EGG\model.egg")
        self.stl.setHpr(self.original_rotation_z + self.rotation_z,
                        self.original_rotation_y + self.rotation_y, 
                        self.original_rotation_x + self.rotation_x)
        pt1, pt2 = self.stl.getTightBounds()
        self.stl.setTransparency(TransparencyAttrib.MAlpha)
        self.stl.setColorScale(0.3, 0.3, 0.3, 1)
        self.stl.setPos(self.location_x + self.origin_x, 
                        self.location_y + self.origin_y, 
                        self.location_z + self.origin_z)
        self.stl.setScale(1, 1, 1)
        self.stl.reparentTo(self.render)
        
        #Display the dimensions of the model
        pt1, pt2 = self.stl.getTightBounds()  
        self.dimension_x = round(max(pt1[0], pt2[0]) - min(pt1[0], pt2[0]), 2)
        self.dimension_y = round(max(pt1[1], pt2[1]) - min(pt1[1], pt2[1]), 2)
        self.dimension_z = round(max(pt1[2], pt2[2]) - min(pt1[2], pt2[2]), 2)
        
        #Show center of mesh
        self.displayMeshCenter()
        
        #Logo placed at top left corner of screen
        self.logo.destroy()
        self.logo = OnscreenImage(image = r"\GRAPHICS\logo_start_screen.png",
                                  pos = (-1.3, 0, 0.83), 
                                  scale = (0.45, 0.15, 0.15))
        self.logo.setTransparency(TransparencyAttrib.MAlpha)
        
        #Display the prepare gcode Button
        self.prepare_gcode_button = DirectButton(image = (r"\GRAPHICS\button_unselect.png", 
                                                          r"\GRAPHICS\button_select.png",
                                                          r"\GRAPHICS\button_select.png", 
                                                          r"\GRAPHICS\button_select.png"),
                                                 relief = None, 
                                                 scale = (0.25, 0.12, 0.05), 
                                                 command = self.prepareGcodeButton,
                                                 pos = (-1.35, 0, -0.8))
        self.prepare_gcode_button.setTransparency(TransparencyAttrib.MAlpha)
        self.prepare_gcode_button.resetFrameSize()
        
        #Display STL upload button text
        self.prepare_gcode_button_label = TextNode('Text')
        self.prepare_gcode_button_label.setText("Prepare Gcode")
        node = aspect2d.attachNewNode(self.prepare_gcode_button_label)
        self.prepare_gcode_button_label_NodePath = node
        self.prepare_gcode_button_label_NodePath.setScale(0.05)
        self.prepare_gcode_button_label.setFont(self.font)
        self.prepare_gcode_button_label_NodePath.setPos(-1.56, 0, -0.81)
        
         #Starting tab (print settings)
        self.printSettingsTabStatus(True)
        
        #Starting tab (print settings)
        self.layerViewerTabStatus(True)
        
        self.done = True
        
        
    def displayMeshCenter (self) -> None:
        #Show coordiante axis
        self.origin = self.loader.loadModel(r"\EGG\origin.egg")
        self.x_axis = self.loader.loadModel(r"\EGG\arrow.egg")
        self.y_axis = self.loader.loadModel(r"\EGG\arrow.egg")
        self.z_axis = self.loader.loadModel(r"\EGG\arrow.egg")
        
        #Make the coordinate axis viewable through the model
        self.origin.setBin("fixed", 0)
        self.origin.setDepthTest(False)
        self.origin.setDepthWrite(False)
        self.x_axis.setBin("fixed", 0)
        self.x_axis.setDepthTest(False)
        self.x_axis.setDepthWrite(False)
        self.y_axis.setBin("fixed", 0)
        self.y_axis.setDepthTest(False)
        self.y_axis.setDepthWrite(False)
        self.z_axis.setBin("fixed", 0)
        self.z_axis.setDepthTest(False)
        self.z_axis.setDepthWrite(False)
        
        #color the axis
        self.origin.setColorScale(1, 1, 1, 1)
        self.x_axis.setColorScale(255, 0, 0, 1)
        self.y_axis.setColorScale(0, 255, 0, 1)
        self.z_axis.setColorScale(0, 0, 255, 1)
        
        #Center it the coordinate axis at the center of the model
        pt1, pt2 = self.stl.getTightBounds()
        self.x_stl = (max(pt1[0], pt2[0]) + min(pt1[0], pt2[0])) / 2
        self.y_stl = (max(pt1[1], pt2[1]) + min(pt1[1], pt2[1])) / 2
        self.z_stl = (max(pt1[2], pt2[2]) + min(pt1[2], pt2[2])) / 2 
        self.origin.setPos(self.x_stl, self.y_stl, self.z_stl)
        self.x_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
        self.y_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
        self.z_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
        self.x_axis.setHpr(90, 90, 0)
        self.y_axis.setHpr(180, 90, 0)
        self.z_axis.setHpr(0, 0, 0)
        self.origin.setScale(1, 1, 1)
        self.x_axis.setScale(4, 4, 4)
        self.y_axis.setScale(4, 4, 4)
        self.z_axis.setScale(4, 4, 4)
        
        #render the coordinate axis
        self.x_axis.reparentTo(self.render)
        self.y_axis.reparentTo(self.render)
        self.z_axis.reparentTo(self.render)
        self.origin.reparentTo(self.render)
    
    def printSettingsTabStatus(self, status:bool) -> None:
        if status:
            try:
                #Clear tabs
                self.tab_space.destroy()
                self.printSettingsTab.destroy()
                self.preferencesTab.destroy()
                self.meshTransformTab.destroy()
            except AttributeError:
                pass
            self.tab_space = OnscreenImage(image = r"\GRAPHICS\tab_3.png",
                                           pos=(1.67, 0, -0.13), 
                                           scale = (0.8, 0.95, 0.95))
            self.printSettingsTab = DirectCheckButton(pos = (1.185, 0, 0.88),
                                                      scale = (0.15, 0.10, 0.06),
                                                      command = self.printSettingsTabStatus, 
                                                      boxRelief = None, 
                                                      pressEffect = 0, 
                                                      boxImage = (r"\GRAPHICS\print_settings_selected_tab.png"), 
                                                      relief = None)
            self.preferencesTab = DirectCheckButton(pos = (1.485, 0, 0.88),
                                                    scale = (0.15, 0.10, 0.06),
                                                    command = self.preferencesTabStatus, 
                                                    boxRelief = None, 
                                                    pressEffect = 0, 
                                                    boxImage = (r"\GRAPHICS\preferences_deselected_tab.png", 
                                                                r"\GRAPHICS\preferences_selected_tab.png", 
                                                                r"\GRAPHICS\preferences_selected_tab.png"), 
                                                    relief = None)
            self.meshTransformTab = DirectCheckButton(pos = (1.785, 0, 0.88),
                                                      scale = (0.15, 0.10, 0.06),
                                                      command = self.meshTransformTabStatus, 
                                                      boxRelief = None, 
                                                      pressEffect = 0, 
                                                      boxImage = (r"\GRAPHICS\mesh_transform_deselected_tab.png", 
                                                                  r"\GRAPHICS\mesh_transform_selected_tab.png", 
                                                                  r"\GRAPHICS\mesh_transform_selected_tab.png"), 
                                                      relief = None)
            
            self.tab_space.setTransparency(TransparencyAttrib.MAlpha)
            self.printSettingsTab.setTransparency(TransparencyAttrib.MAlpha)
            self.preferencesTab.setTransparency(TransparencyAttrib.MAlpha)
            self.meshTransformTab.setTransparency(TransparencyAttrib.MAlpha)
            #Show info on print settings tab
            self.printSettingsInfo()
            
        else:
            pass
            
    def meshTransformTabStatus (self, status:bool) -> None:
        if status:
            try:
                #Clear tabs
                self.tab_space.destroy()
                self.printSettingsTab.destroy()
                self.preferencesTab.destroy()
                self.meshTransformTab.destroy()
            except AttributeError:
                pass
            self.tab_space = OnscreenImage(image = r"\GRAPHICS\tab_3.png",
                                           pos = (1.67, 0, -0.13), 
                                           scale = (0.8, 0.95, 0.95))
            self.tab_space.setTransparency(TransparencyAttrib.MAlpha)
            self.printSettingsTab = DirectCheckButton(pos = (1.185, 0, 0.88),
                                                      scale = (0.15, 0.10, 0.06),
                                                      command = self.printSettingsTabStatus, 
                                                      boxRelief = None, 
                                                      pressEffect = 0, 
                                                      boxImage = (r"\GRAPHICS\print_settings_deselected_tab.png", 
                                                                  r"\GRAPHICS\print_settings_selected_tab.png", 
                                                                  r"\GRAPHICS\print_settings_selected_tab.png"), 
                                                      relief = None)
            self.preferencesTab = DirectCheckButton(pos = (1.485, 0, 0.88),
                                                    scale = (0.15, 0.10, 0.06),
                                                    command = self.preferencesTabStatus, 
                                                    boxRelief = None, 
                                                    pressEffect = 0, 
                                                    boxImage = (r"\GRAPHICS\preferences_deselected_tab.png", 
                                                                r"\GRAPHICS\preferences_selected_tab.png", 
                                                                r"\GRAPHICS\preferences_selected_tab.png"), 
                                                    relief = None)
            self.meshTransformTab = DirectCheckButton(pos = (1.785, 0, 0.88),
                                                      scale = (0.15, 0.10, 0.06),
                                                      command = self.meshTransformTabStatus, 
                                                      boxRelief = None, 
                                                      pressEffect = 0, 
                                                      boxImage = (r"\GRAPHICS\mesh_transform_selected_tab.png"), 
                                                      relief = None)
            
            self.tab_space.setTransparency(TransparencyAttrib.MAlpha)
            self.printSettingsTab.setTransparency(TransparencyAttrib.MAlpha)
            self.preferencesTab.setTransparency(TransparencyAttrib.MAlpha)
            self.meshTransformTab.setTransparency(TransparencyAttrib.MAlpha)
            #Show info on mesh transform tab
            self.meshTransformInfo()
        else:
            pass
            
    def preferencesTabStatus (self, status:bool) -> None:
        if status:
            try:
                #Clear tabs
                self.tab_space.destroy()
                self.printSettingsTab.destroy()
                self.preferencesTab.destroy()
                self.meshTransformTab.destroy()
            except AttributeError:
                pass
            self.tab_space = OnscreenImage(image = r"\GRAPHICS\tab_3.png",
                                           pos = (1.67, 0, -0.13), 
                                           scale = (0.8, 0.95, 0.95))
            self.tab_space.setTransparency(TransparencyAttrib.MAlpha)
            self.printSettingsTab = DirectCheckButton(pos = (1.185, 0, 0.88),
                                                      scale = (0.15, 0.10, 0.06),
                                                      command = self.printSettingsTabStatus, 
                                                      boxRelief = None, 
                                                      pressEffect = 0, 
                                                      boxImage = (r"\GRAPHICS\print_settings_deselected_tab.png", 
                                                                  r"\GRAPHICS\print_settings_selected_tab.png", 
                                                                  r"\GRAPHICS\print_settings_selected_tab.png"), 
                                                      relief = None)
            self.preferencesTab = DirectCheckButton(pos = (1.485, 0, 0.88),
                                                    scale = (0.15, 0.10, 0.06),
                                                    command = self.preferencesTabStatus, 
                                                    boxRelief = None, 
                                                    pressEffect = 0, 
                                                    boxImage = (r"\GRAPHICS\preferences_selected_tab.png"), 
                                                    relief = None)
            self.meshTransformTab = DirectCheckButton(pos = (1.785, 0, 0.88),
                                                      scale = (0.15, 0.10, 0.06),
                                                      command = self.meshTransformTabStatus, 
                                                      boxRelief = None, 
                                                      pressEffect = 0, 
                                                      boxImage = (r"\GRAPHICS\mesh_transform_deselected_tab.png", 
                                                                  r"\GRAPHICS\mesh_transform_selected_tab.png", 
                                                                  r"\GRAPHICS\mesh_transform_selected_tab.png"), 
                                                      relief = None)
                                                      
            self.tab_space.setTransparency(TransparencyAttrib.MAlpha)
            self.printSettingsTab.setTransparency(TransparencyAttrib.MAlpha)
            self.preferencesTab.setTransparency(TransparencyAttrib.MAlpha)
            self.meshTransformTab.setTransparency(TransparencyAttrib.MAlpha)
            #Show info on preferences tab
            self.preferencesInfo()
        else:
            pass
    
    def layerViewerTabStatus (self, status:bool) -> None:
        if status:
            self.left_tab_space = OnscreenImage(image = r"\GRAPHICS\tab_3.png",
                                                pos = (-1.67, 0, -0.05), 
                                                 scale = (0.8, 0.95, 0.6))
            self.tab_space.setTransparency(TransparencyAttrib.MAlpha)
            self.layerViewerInfo()
        else:
            pass
        
    def printSettingsInfo(self) -> None:
        #Info on starting tab (print settings)
        #Display layer height text
        self.layer_height_label = TextNode('Text')
        self.layer_height_label.setText("Layer Height:") 
        node = aspect2d.attachNewNode(self.layer_height_label)
        self.layer_height_label_NodePath = node
        self.layer_height_label_NodePath.setScale(0.03)
        self.layer_height_label.setFont(self.font)
        self.layer_height_label_NodePath.setPos(0.9, 0, 0.7)
        
        #Display mm text 
        self.layer_height_label_mm = TextNode('Text')
        self.layer_height_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.layer_height_label_mm)
        self.layer_height_label_mm_NodePath = node
        self.layer_height_label_mm_NodePath.setScale(0.03)
        self.layer_height_label_mm.setFont(self.font)
        self.layer_height_label_mm_NodePath.setPos(1.5, 0, 0.7)
        
        #Display default layer height value
        self.layer_height_value = TextNode('Text')
        self.layer_height_value.setText(f"{self.layer_height}") 
        node = aspect2d.attachNewNode(self.layer_height_value)
        self.layer_height_value_NodePath = node
        self.layer_height_value_NodePath.setScale(0.03)
        self.layer_height_value.setFont(self.font)
        self.layer_height_value_NodePath.setPos(1.31, 0, 0.7)
        
        #Display print speed text
        self.print_speed_label = TextNode('Text')
        self.print_speed_label.setText("Print Speed:") 
        node = aspect2d.attachNewNode(self.print_speed_label)
        self.print_speed_label_NodePath = node
        self.print_speed_label_NodePath.setScale(0.03)
        self.print_speed_label.setFont(self.font)
        self.print_speed_label_NodePath.setPos(0.9, 0, 0.6)
        
        #Display mm/s text 
        self.print_speed_label_speed = TextNode('Text')
        self.print_speed_label_speed.setText("mm/s") 
        node = aspect2d.attachNewNode(self.print_speed_label_speed)
        self.print_speed_label_speed_NodePath = node
        self.print_speed_label_speed_NodePath.setScale(0.03)
        self.print_speed_label_speed.setFont(self.font)
        self.print_speed_label_speed_NodePath.setPos(1.5, 0, 0.6)
        
        #Display default print speed value
        self.print_speed_value = TextNode('Text')
        self.print_speed_value.setText(f"{self.print_speed}") 
        self.print_speed_value_NodePath = aspect2d.attachNewNode(self.print_speed_value)
        self.print_speed_value_NodePath.setScale(0.03)
        self.print_speed_value.setFont(self.font)
        self.print_speed_value_NodePath.setPos(1.32, 0, 0.6)
        
        #Display Infill percentage text
        self.infill_percentage_label = TextNode('Text')
        self.infill_percentage_label.setText("Infill Percentage:") 
        node = aspect2d.attachNewNode(self.infill_percentage_label)
        self.infill_percentage_label_NodePath = node
        self.infill_percentage_label_NodePath.setScale(0.03)
        self.infill_percentage_label.setFont(self.font)
        self.infill_percentage_label_NodePath.setPos(0.9, 0, 0.5)
        
        #Display % text 
        self.infill_percentage_label_percent = TextNode('Text')
        self.infill_percentage_label_percent.setText("%") 
        node = aspect2d.attachNewNode(self.infill_percentage_label_percent)
        self.infill_percentage_label_percent_NodePath = node 
        self.infill_percentage_label_percent_NodePath.setScale(0.03)
        self.infill_percentage_label_percent.setFont(self.font)
        self.infill_percentage_label_percent_NodePath.setPos(1.5, 0, 0.5)
        
        #Display default infill percentage value
        self.infill_percentage_value = TextNode('Text')
        self.infill_percentage_value.setText(f"{self.infill_percentage}") 
        node = aspect2d.attachNewNode(self.infill_percentage_value)
        self.infill_percentage_value_NodePath = node
        self.infill_percentage_value_NodePath.setScale(0.03)
        self.infill_percentage_value.setFont(self.font)
        self.infill_percentage_value_NodePath.setPos(1.31, 0, 0.5)
        
        #Display print temperature text
        self.print_temperature_label = TextNode('Text')
        self.print_temperature_label.setText("Print Temperature:")
        node = aspect2d.attachNewNode(self.print_temperature_label)
        self.print_temperature_label_NodePath = node
        self.print_temperature_label_NodePath.setScale(0.03)
        self.print_temperature_label.setFont(self.font)
        self.print_temperature_label_NodePath.setPos(0.9, 0, 0.4)
        
        #Display degrees celsius text 
        self.print_temperature_label_degree_celsius = TextNode('Text')
        self.print_temperature_label_degree_celsius.setText("\N{DEGREE SIGN}C") 
        node = aspect2d.attachNewNode(self.print_temperature_label_degree_celsius)
        self.print_temperature_label_degree_celsius_NodePath = node
        self.print_temperature_label_degree_celsius_NodePath.setScale(0.03)
        self.print_temperature_label_degree_celsius.setFont(self.font)
        self.print_temperature_label_degree_celsius_NodePath.setPos(1.5,0,0.4)
        
        #Display default print temperature value
        self.print_temperature_value = TextNode('Text')
        self.print_temperature_value.setText(f"{self.print_temperature}") 
        self.print_temperature_value_NodePath = aspect2d.attachNewNode(self.print_temperature_value)
        self.print_temperature_value_NodePath.setScale(0.03)
        self.print_temperature_value.setFont(self.font)
        self.print_temperature_value_NodePath.setPos(1.31, 0, 0.4)
        
        #Display retraction length button text
        self.retraction_length_label = TextNode('Text')
        self.retraction_length_label.setText("Retraction Length:") 
        node = aspect2d.attachNewNode(self.retraction_length_label)
        self.retraction_length_label_NodePath = node
        self.retraction_length_label_NodePath.setScale(0.03)
        self.retraction_length_label.setFont(self.font)
        self.retraction_length_label_NodePath.setPos(0.9, 0, 0.3)
        
        #Display mm button text 
        self.retraction_length_label_mm = TextNode('Text')
        self.retraction_length_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.retraction_length_label_mm)
        self.retraction_length_label_mm_NodePath = node
        self.retraction_length_label_mm_NodePath.setScale(0.03)
        self.retraction_length_label_mm.setFont(self.font)
        self.retraction_length_label_mm_NodePath.setPos(1.5, 0, 0.3)
        
        #Display default retraction length value
        self.retraction_length_value = TextNode('Text')
        self.retraction_length_value.setText(f"{self.retraction_length}") 
        node = aspect2d.attachNewNode(self.retraction_length_value)
        self.retraction_length_value_NodePath = node
        self.retraction_length_value_NodePath.setScale(0.03)
        self.retraction_length_value.setFont(self.font)
        self.retraction_length_value_NodePath.setPos(1.32, 0, 0.3)
        
        #Display retraction speed text
        self.retraction_speed_label = TextNode('Text')
        self.retraction_speed_label.setText("Retraction Speed:") 
        node = aspect2d.attachNewNode(self.retraction_speed_label)
        self.retraction_speed_label_NodePath = node 
        self.retraction_speed_label_NodePath.setScale(0.03)
        self.retraction_speed_label.setFont(self.font)
        self.retraction_speed_label_NodePath.setPos(0.9, 0, 0.2)
        
        #Display mm/s text 
        self.retraction_speed_label_speed = TextNode('Text')
        self.retraction_speed_label_speed.setText("mm/s")
        node = aspect2d.attachNewNode(self.retraction_speed_label_speed)
        self.retraction_speed_label_speed_NodePath = node
        self.retraction_speed_label_speed_NodePath.setScale(0.03)
        self.retraction_speed_label_speed.setFont(self.font)
        self.retraction_speed_label_speed_NodePath.setPos(1.5, 0, 0.2)
        
        #Display default retraction speed value
        self.retraction_speed_value = TextNode('Text')
        self.retraction_speed_value.setText(f"{self.retraction_speed}") 
        node = aspect2d.attachNewNode(self.retraction_speed_value)
        self.retraction_speed_value_NodePath = node
        self.retraction_speed_value_NodePath.setScale(0.03)
        self.retraction_speed_value.setFont(self.font)
        self.retraction_speed_value_NodePath.setPos(1.32, 0, 0.2)
        
        #Display nozzle diameter text
        self.nozzle_diameter_label = TextNode('Text')
        self.nozzle_diameter_label.setText("Nozzle Diameter:") 
        node = aspect2d.attachNewNode(self.nozzle_diameter_label)
        self.nozzle_diameter_label_NodePath = node
        self.nozzle_diameter_label_NodePath.setScale(0.03)
        self.nozzle_diameter_label.setFont(self.font)
        self.nozzle_diameter_label_NodePath.setPos(0.9, 0, 0.1)
        
        #Display mm text 
        self.nozzle_diameter_label_mm = TextNode('Text')
        self.nozzle_diameter_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.nozzle_diameter_label_mm)
        self.nozzle_diameter_label_mm_NodePath = node
        self.nozzle_diameter_label_mm_NodePath.setScale(0.03)
        self.nozzle_diameter_label_mm.setFont(self.font)
        self.nozzle_diameter_label_mm_NodePath.setPos(1.5, 0, 0.1)
        
        #Display default nozzle diameter value
        self.nozzle_diameter_value = TextNode('Text')
        self.nozzle_diameter_value.setText(f"{self.nozzle_diameter}") 
        node = aspect2d.attachNewNode(self.nozzle_diameter_value)
        self.nozzle_diameter_value_NodePath = node
        self.nozzle_diameter_value_NodePath.setScale(0.03)
        self.nozzle_diameter_value.setFont(self.font)
        self.nozzle_diameter_value_NodePath.setPos(1.31, 0, 0.1)
        
        #Display wall line count text
        self.wall_line_count_label = TextNode('Text')
        self.wall_line_count_label.setText("Wall Line Count:")
        node = aspect2d.attachNewNode(self.wall_line_count_label)
        self.wall_line_count_label_NodePath = node
        self.wall_line_count_label_NodePath.setScale(0.03)
        self.wall_line_count_label.setFont(self.font)
        self.wall_line_count_label_NodePath.setPos(0.9, 0, 0)
        
        #Display # text 
        self.wall_line_count_label_number = TextNode('Text')
        self.wall_line_count_label_number.setText("#") 
        node = aspect2d.attachNewNode(self.wall_line_count_label_number)
        self.wall_line_count_label_number_NodePath = node 
        self.wall_line_count_label_number_NodePath.setScale(0.03)
        self.wall_line_count_label_number.setFont(self.font)
        self.wall_line_count_label_number_NodePath.setPos(1.5, 0, 0)
        
        #Display default wall line count value
        self.wall_line_count_value = TextNode('Text')
        self.wall_line_count_value.setText(f"{self.wall_line_count}")
        node = aspect2d.attachNewNode(self.wall_line_count_value)
        self.wall_line_count_value_NodePath = node
        self.wall_line_count_value_NodePath.setScale(0.03)
        self.wall_line_count_value.setFont(self.font)
        self.wall_line_count_value_NodePath.setPos(1.33, 0, 0)
        
        #Display cylinder diameter text
        self.cylinder_diameter_label = TextNode('Text')
        self.cylinder_diameter_label.setText("Cylinder Diameter:")
        node = aspect2d.attachNewNode(self.cylinder_diameter_label)
        self.cylinder_diameter_label_NodePath = node
        self.cylinder_diameter_label_NodePath.setScale(0.03)
        self.cylinder_diameter_label.setFont(self.font)
        self.cylinder_diameter_label_NodePath.setPos(0.9, 0, -0.1)
        
        #Display mm text 
        self.cylinder_diameter_label_mm = TextNode('Text')
        self.cylinder_diameter_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.cylinder_diameter_label_mm)
        self.cylinder_diameter_label_mm_NodePath = node 
        self.cylinder_diameter_label_mm_NodePath.setScale(0.03)
        self.cylinder_diameter_label_mm.setFont(self.font)
        self.cylinder_diameter_label_mm_NodePath.setPos(1.5, 0, -0.1)
        
        #Display default cylinder diameter count value
        self.cylinder_diameter_value = TextNode('Text')
        self.cylinder_diameter_value.setText(f"{self.cylinder_diameter}")
        node = aspect2d.attachNewNode(self.cylinder_diameter_value)
        self.cylinder_diameter_value_NodePath = node
        self.cylinder_diameter_value_NodePath.setScale(0.03)
        self.cylinder_diameter_value.setFont(self.font)
        self.cylinder_diameter_value_NodePath.setPos(1.31, 0, -0.1)
        
        #Display delta y text
        self.delta_y_label = TextNode('Text')
        self.delta_y_label.setText("Delta Y:")
        node = aspect2d.attachNewNode(self.delta_y_label)
        self.delta_y_label_NodePath = node
        self.delta_y_label_NodePath.setScale(0.03)
        self.delta_y_label.setFont(self.font)
        self.delta_y_label_NodePath.setPos(0.9, 0, -0.2)
        
        #Display mm text 
        self.delta_y_label_mm = TextNode('Text')
        self.delta_y_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.delta_y_label_mm)
        self.delta_y_label_mm_NodePath = node 
        self.delta_y_label_mm_NodePath.setScale(0.03)
        self.delta_y_label_mm.setFont(self.font)
        self.delta_y_label_mm_NodePath.setPos(1.5, 0, -0.2)
        
        #Display default delta y value
        self.delta_y_value = TextNode('Text')
        self.delta_y_value.setText(f"{self.delta_y}")
        node = aspect2d.attachNewNode(self.delta_y_value)
        self.delta_y_value_NodePath = node
        self.delta_y_value_NodePath.setScale(0.03)
        self.delta_y_value.setFont(self.font)
        self.delta_y_value_NodePath.setPos(1.31, 0, -0.2)
        
        #Display cylinder length text
        self.cylinder_length_label = TextNode('Text')
        self.cylinder_length_label.setText("Cylinder Length:")
        node = aspect2d.attachNewNode(self.cylinder_length_label)
        self.cylinder_length_label_NodePath = node
        self.cylinder_length_label_NodePath.setScale(0.03)
        self.cylinder_length_label.setFont(self.font)
        self.cylinder_length_label_NodePath.setPos(0.9, 0, -0.3)
        
        #Display mm text 
        self.cylinder_length_label_mm = TextNode('Text')
        self.cylinder_length_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.cylinder_length_label_mm)
        self.cylinder_length_label_mm_NodePath = node 
        self.cylinder_length_label_mm_NodePath.setScale(0.03)
        self.cylinder_length_label_mm.setFont(self.font)
        self.cylinder_length_label_mm_NodePath.setPos(1.5, 0, -0.3)
        
        #Display default cylinder length value
        self.cylinder_length_value = TextNode('Text')
        self.cylinder_length_value.setText(f"{self.cylinder_length}")
        node = aspect2d.attachNewNode(self.cylinder_length_value)
        self.cylinder_length_value_NodePath = node
        self.cylinder_length_value_NodePath.setScale(0.03)
        self.cylinder_length_value.setFont(self.font)
        self.cylinder_length_value_NodePath.setPos(1.31, 0, -0.3)
        
        #Display filament diameter text
        self.filament_diameter_label = TextNode('Text')
        self.filament_diameter_label.setText("Filament Diameter:")
        node = aspect2d.attachNewNode(self.filament_diameter_label)
        self.filament_diameter_label_NodePath = node
        self.filament_diameter_label_NodePath.setScale(0.03)
        self.filament_diameter_label.setFont(self.font)
        self.filament_diameter_label_NodePath.setPos(0.9, 0, -0.4)
        
        #Display mm text 
        self.filament_diameter_label_mm = TextNode('Text')
        self.filament_diameter_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.filament_diameter_label_mm)
        self.filament_diameter_label_mm_NodePath = node 
        self.filament_diameter_label_mm_NodePath.setScale(0.03)
        self.filament_diameter_label_mm.setFont(self.font)
        self.filament_diameter_label_mm_NodePath.setPos(1.5, 0, -0.4)
        
        #Display default filament diameter value
        self.filament_diameter_value = TextNode('Text')
        self.filament_diameter_value.setText(f"{self.filament_diameter}")
        node = aspect2d.attachNewNode(self.filament_diameter_value)
        self.filament_diameter_value_NodePath = node
        self.filament_diameter_value_NodePath.setScale(0.03)
        self.filament_diameter_value.setFont(self.font)
        self.filament_diameter_value_NodePath.setPos(1.31, 0, -0.4)
        
        #Display Infill Orientation text
        self.infill_orientation_label = TextNode('Text')
        self.infill_orientation_label.setText("Infill Orientation:")
        node = aspect2d.attachNewNode(self.infill_orientation_label)
        self.infill_orientation_label_NodePath = node
        self.infill_orientation_label_NodePath.setScale(0.03)
        self.infill_orientation_label.setFont(self.font)
        self.infill_orientation_label_NodePath.setPos(0.9, 0, -0.5)
        
        #Display degree text 
        self.infill_orientation_label_degree_celsius = TextNode('Text')
        self.infill_orientation_label_degree_celsius.setText("\N{DEGREE SIGN}") 
        node = aspect2d.attachNewNode(self.infill_orientation_label_degree_celsius)
        self.infill_orientation_label_degree_celsius_NodePath = node
        self.infill_orientation_label_degree_celsius_NodePath.setScale(0.03)
        self.infill_orientation_label_degree_celsius.setFont(self.font)
        self.infill_orientation_label_degree_celsius_NodePath.setPos(1.5, 0, -0.5)
        
        #Display default Infill Orientation value
        self.infill_orientation_value = TextNode('Text')
        self.infill_orientation_value.setText(f"{self.infill_orientation}") 
        self.infill_orientation_value_NodePath = aspect2d.attachNewNode(self.infill_orientation_value)
        self.infill_orientation_value_NodePath.setScale(0.03)
        self.infill_orientation_value.setFont(self.font)
        self.infill_orientation_value_NodePath.setPos(1.31, 0, -0.5)
        
        
    def layerViewerInfo(self) -> None:
        slicer = cs.cylindrical_slicer(self.stl_file_address, 
                                       self.nozzle_diameter, 
                                       self.rotation_x, 
                                       self.rotation_y, 
                                       self.rotation_z, 
                                       self.location_x, 
                                       self.location_y, 
                                       self.location_z, 
                                       self.cylinder_diameter, 
                                       self.delta_y)
        #Layer count 
        self.layer_count =int((slicer.max_radius - (self.cylinder_diameter / 2)) / self.layer_height) - 1
        radius = self.layer_height * self.layer_number + (self.cylinder_diameter / 2)
        edges = slicer.gather_edges(radius)
        if str(edges) != "error":
            #Create a picture of the layer
            layer_sim = layersim.layer_viewer(edges, radius, self.layer_number,
                                              self.location_x, self.location_y,
                                              self.location_z, self.rotation_x,
                                              self.rotation_y, self.rotation_z)
            image_address = (f"LAYERS\\layer_{self.layer_number}_" +
                             f"{self.location_x}_{self.location_y}_{self.location_z}_" +
                             f"{self.rotation_x}_{self.rotation_y}_{self.rotation_z}" +
                             ".png")
            
            self.layer = OnscreenImage(image = image_address,
                                       pos = (-1.34, 0, 0), 
                                       scale = (0.3, 0.3, 0.3),
                                       hpr = (0, 0, 0))
        else:
            self.layer = OnscreenImage(image = f"\LAYERS\error.png",
                                       pos = (-1.34, 0, 0), 
                                       scale = (0.3, 0.3, 0.3),
                                       hpr = (0, 0, 0))
            
        
        radius = round(radius, 2)
        self.label_radius = OnscreenText(text = f"{round(radius, 2)}", 
                                         pos = (-1.36, -0.535),
                                         fg = (1, 1, 1, 1), 
                                         font = self.font,
                                         scale=0.03)
        
        self.label_layer_count = OnscreenText(text = f"/{self.layer_count}", 
                                              pos = (-1.21, -0.385), 
                                              fg = (1, 1, 1, 1), 
                                              font = self.font,
                                              scale = 0.03)
         
        self.layer_number_entry = DirectEntry(text = "", 
                                  scale = 0.03, 
                                  command = self.setTextLayerNumber,
                                  initialText = f"{self.layer_number}", 
                                  numLines = 5, 
                                  focus = 0, 
                                  relief = None, 
                                  text_fg = (1, 1, 1, 1), 
                                  text_font = self.font, 
                                  width = 9)
        self.layer_number_entry.setPos(-1.41, 0, -0.385)
        layer_viewer_text = "                        Unwrapped Layer View:"
        self.label_layer_viewer_before_tilt = OnscreenText(text = layer_viewer_text, 
                                                           pos = (-1.46, 0.4), 
                                                           fg = (1, 1, 1, 1), 
                                                           font = self.font,
                                                           scale = 0.03)
        
        self.label_layer_number = OnscreenText(text = "Layer:", 
                                               pos = (-1.49, -0.385), 
                                               fg = (1, 1, 1, 1), 
                                               font = self.font,
                                               scale = 0.03)
        
        self.label_radius_text= OnscreenText(text = "Radius:", 
                                             pos = (-1.49, -0.535), 
                                             fg = (1, 1, 1, 1), 
                                             font = self.font,
                                             scale = 0.03)
        
        self.label_mm = OnscreenText(text = "mm", 
                                     pos = (-1.21, -0.535), 
                                     fg = (1, 1, 1, 1), 
                                     font = self.font,
                                     scale = 0.03)
        
        type_box_text = "                   "
        self.textObject = OnscreenText(text = type_box_text, 
                                       pos = (-1.29, -0.39), 
                                       scale = 0.05,
                                       frame = (1, 1, 1, 1))
        
        type_box_text = "                   "
        self.textObject = OnscreenText(text = type_box_text, 
                                       pos = (-1.29, -0.54), 
                                       scale = 0.05,
                                       frame = (1, 1, 1, 1))
    
    def preferencesInfo(self) -> None:
        #Start Gcode
        start_gcode = "Start G-code:"
        self.label_start_gcode = OnscreenText(text = start_gcode, 
                                              pos = (1.02, 0.76), 
                                              scale = 0.03, 
                                              fg = (1, 1, 1, 1), 
                                              font = self.font)
        
        self.start_gcode_entry = OnscreenText(text = self.start_gcode, 
                                              pos = (1.05, 0.71), 
                                              scale = 0.03, 
                                              fg = (1, 1, 1, 1), 
                                              font = self.font,
                                              align=False)
        
        #End Gcode
        end_gcode_text = "End G-code:"
        self.label_end_gcode = OnscreenText(text = end_gcode_text, 
                                            pos = (1.01, 0.05),
                                            scale = 0.03, 
                                            fg = (1, 1, 1, 1), 
                                            font = self.font)
        self.end_gcode_entry = OnscreenText(text = self.end_gcode, 
                                            pos = (1.05, 0.), 
                                            scale = 0.03, 
                                            fg = (1, 1, 1, 1), 
                                            font = self.font,
                                            align=False)
        
        
        #Flavor
        flavor_text = "Flavor:"
        self.label_flavor = OnscreenText(text= flavor_text, 
                                         pos = (0.99, -0.72), 
                                         scale = 0.03, 
                                         fg = (1,1,1,1), 
                                         font = self.font)
        self.flavor_entry = OnscreenText(text = self.flavor, 
                                         pos = (1.05, -0.76), 
                                         scale = 0.03, 
                                         fg = (1, 1, 1, 1), 
                                         font = self.font,
                                         align=False)
        
        #Header
        header_text = "Header:"
        self.label_flavor = OnscreenText(text= header_text, 
                                               pos = (0.99, -0.46), 
                                               scale = 0.03, 
                                               fg = (1, 1, 1, 1), 
                                               font = self.font)
        self.header_entry = OnscreenText(text = self.header, 
                                         pos = (1.05, -0.505), 
                                         scale = 0.03, 
                                         fg = (1, 1, 1, 1), 
                                         font = self.font,
                                         align=False)
        
    def setTextLayerNumber(self, textEntered:str) -> None:
        slicer = cs.cylindrical_slicer(self.stl_file_address, 
                                       self.nozzle_diameter, 
                                       self.rotation_x, 
                                       self.rotation_y, 
                                       self.rotation_z, 
                                       self.location_x, 
                                       self.location_y, 
                                       self.location_z, 
                                       self.cylinder_diameter, 
                                       self.delta_y)
        try:
            self.layer_number = int(textEntered)
            self.layer_count = int((slicer.max_radius - (self.cylinder_diameter / 2)) / self.layer_height) - 1
            radius = self.layer_height * self.layer_number + (self.cylinder_diameter / 2)
            edges = slicer.gather_edges(radius)
            radius = round(radius, 2)
        except ValueError:
            edges = "error"
            radius = "nan"
        
        if str(edges) != "error":
            self.layer.destroy()
            layer_sim = layersim.layer_viewer(edges, radius, self.layer_number,
                                              self.location_x, self.location_y,
                                              self.location_z, self.rotation_x,
                                              self.rotation_y, self.rotation_z)
            image_address = (f"LAYERS\\layer_{self.layer_number}_" +
                             f"{self.location_x}_{self.location_y}_{self.location_z}_" +
                             f"{self.rotation_x}_{self.rotation_y}_{self.rotation_z}" +
                              ".png")
            self.layer = OnscreenImage(image = image_address,
                                       pos = (-1.34, 0, 0), 
                                       scale = (0.3, 0.3, 0.3),
                                       hpr = (0, 0, 0))
        else: 
            self.layer.destroy()
            self.layer = OnscreenImage(image = r"\LAYERS\error.png",
                                       pos = (-1.34, 0, 0), 
                                       scale = (0.3, 0.3, 0.3),
                                       hpr = (0, 0, 0))
        self.label_radius.destroy()
        self.label_radius = OnscreenText(text = f"{radius}", 
                                         pos = (-1.36, -0.535), 
                                         fg = (1, 1, 1, 1), 
                                         font = self.font,
                                         scale = 0.03)
    
    def meshTransformInfo(self) -> None:
        #Info on mesh transform tab 
        #Display location buttons
        self.location_x_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png",
                                                       r"\GRAPHICS\rest_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png"),
                                              relief = None, 
                                              scale = (0.1, 0.12, 0.03), 
                                              command = self.locationXButton,
                                              pos = (1.35, 0, 0.71))
        self.location_x_button.setTransparency(TransparencyAttrib.MAlpha)
        self.location_x_button.resetFrameSize()
        
        self.location_y_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png",
                                                       r"\GRAPHICS\rest_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png"),
                                              relief = None, 
                                              scale = (0.1, 0.12, 0.03), 
                                              command = self.locationYButton,
                                              pos = (1.35, 0, 0.61))
        self.location_y_button.setTransparency(TransparencyAttrib.MAlpha)
        self.location_y_button.resetFrameSize()
        
        self.location_z_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png",
                                                       r"\GRAPHICS\rest_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png"),
                                              relief = None, 
                                              scale = (0.1, 0.12, 0.03), 
                                              command = self.locationZButton,
                                              pos = (1.35, 0, 0.51))
        self.location_z_button.setTransparency(TransparencyAttrib.MAlpha)
        self.location_z_button.resetFrameSize()
        
        #Display location button text
        self.location_x_button_label = TextNode('Text')
        self.location_x_button_label.setText("Location X:")
        node = aspect2d.attachNewNode(self.location_x_button_label)
        self.location_x_button_label_NodePath = node
        self.location_x_button_label_NodePath.setScale(0.03)
        self.location_x_button_label.setFont(self.font)
        self.location_x_button_label_NodePath.setPos(0.9, 0, 0.7)
        
        self.location_y_button_label = TextNode('Text')
        self.location_y_button_label.setText("Location Y:") 
        node = aspect2d.attachNewNode(self.location_y_button_label)
        self.location_y_button_label_NodePath = node
        self.location_y_button_label_NodePath.setScale(0.03)
        self.location_y_button_label.setFont(self.font)
        self.location_y_button_label_NodePath.setPos(0.9, 0, 0.6)
        
        self.location_z_button_label = TextNode('Text')
        self.location_z_button_label.setText("Location Z:") 
        node = aspect2d.attachNewNode(self.location_z_button_label)
        self.location_z_button_label_NodePath = node
        self.location_z_button_label_NodePath.setScale(0.03)
        self.location_z_button_label.setFont(self.font)
        self.location_z_button_label_NodePath.setPos(0.9, 0, 0.5)
        
        #Display mm button text 
        self.location_x_button_label_mm = TextNode('Text')
        self.location_x_button_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.location_x_button_label_mm)
        self.location_x_button_label_mm_NodePath = node
        self.location_x_button_label_mm_NodePath.setScale(0.03)
        self.location_x_button_label_mm.setFont(self.font) 
        self.location_x_button_label_mm_NodePath.setPos(1.5, 0, 0.7)
        
        self.location_y_button_label_mm = TextNode('Text')
        self.location_y_button_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.location_y_button_label_mm)
        self.location_y_button_label_mm_NodePath = node
        self.location_y_button_label_mm_NodePath.setScale(0.03)
        self.location_y_button_label_mm.setFont(self.font)
        self.location_y_button_label_mm_NodePath.setPos(1.5, 0, 0.6)
        
        self.location_z_button_label_mm = TextNode('Text')
        self.location_z_button_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.location_z_button_label_mm)
        self.location_z_button_label_mm_NodePath = node
        self.location_z_button_label_mm_NodePath.setScale(0.03)
        self.location_z_button_label_mm.setFont(self.font)
        self.location_z_button_label_mm_NodePath.setPos(1.5, 0, 0.5)
        
        #Display location value
        self.location_x_value = TextNode('Text')
        self.location_x_value.setText(f"{self.location_x}") 
        node = aspect2d.attachNewNode(self.location_x_value)
        self.location_x_value_NodePath = node
        self.location_x_value_NodePath.setScale(0.03)
        self.location_x_value.setFont(self.font)
        self.location_x_value_NodePath.setPos(1.3, 0, 0.7)
        
        self.location_y_value = TextNode('Text')
        self.location_y_value.setText(f"{self.location_y}") 
        node = aspect2d.attachNewNode(self.location_y_value)
        self.location_y_value_NodePath = node
        self.location_y_value_NodePath.setScale(0.03)
        self.location_y_value.setFont(self.font)
        self.location_y_value_NodePath.setPos(1.3, 0, 0.6)
        
        self.location_z_value = TextNode('Text')
        self.location_z_value.setText(f"{self.location_z}") 
        node = aspect2d.attachNewNode(self.location_z_value)
        self.location_z_value_NodePath = node
        self.location_z_value_NodePath.setScale(0.03)
        self.location_z_value.setFont(self.font)
        self.location_z_value_NodePath.setPos(1.3, 0, 0.5)
        
        #Info on mesh transform tab 
        #Display rotation buttons
        self.rotation_x_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png",
                                                       r"\GRAPHICS\rest_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png"),
                                              relief = None, 
                                              scale = (0.1, 0.12, 0.03), 
                                              command = self.rotationXButton,
                                              pos = (1.35, 0, 0.41))
        self.rotation_x_button.setTransparency(TransparencyAttrib.MAlpha)
        self.rotation_x_button.resetFrameSize()
        
        self.rotation_y_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png",
                                                       r"\GRAPHICS\rest_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png"),
                                               relief = None, 
                                               scale = (0.1, 0.12, 0.03), 
                                               command = self.rotationYButton,
                                               pos = (1.35, 0, 0.31))
        self.rotation_y_button.setTransparency(TransparencyAttrib.MAlpha)
        self.rotation_y_button.resetFrameSize()
        
        self.rotation_z_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png",
                                                       r"\GRAPHICS\rest_text_box.png", 
                                                       r"\GRAPHICS\rest_text_box.png"),
                                              relief = None, 
                                              scale = (0.1, 0.12, 0.03), 
                                              command = self.rotationZButton,
                                              pos = (1.35, 0, 0.21))
        self.rotation_z_button.setTransparency(TransparencyAttrib.MAlpha)
        self.rotation_z_button.resetFrameSize()
        
        #Display rotation button text
        self.rotation_x_button_label = TextNode('Text')
        self.rotation_x_button_label.setText("Rotation X Axis:") 
        node = aspect2d.attachNewNode(self.rotation_x_button_label)
        self.rotation_x_button_label_NodePath = node
        self.rotation_x_button_label_NodePath.setScale(0.03)
        self.rotation_x_button_label.setFont(self.font)
        self.rotation_x_button_label_NodePath.setPos(0.9, 0, 0.4)
        
        self.rotation_y_button_label = TextNode('Text')
        self.rotation_y_button_label.setText("Rotation Y Axis:") 
        node = aspect2d.attachNewNode(self.rotation_y_button_label)
        self.rotation_y_button_label_NodePath = node
        self.rotation_y_button_label_NodePath.setScale(0.03)
        self.rotation_y_button_label.setFont(self.font)
        self.rotation_y_button_label_NodePath.setPos(0.9, 0, 0.3)
        
        self.rotation_z_button_label = TextNode('Text')
        self.rotation_z_button_label.setText("Rotation Z Axis:") 
        node = aspect2d.attachNewNode(self.rotation_z_button_label)
        self.rotation_z_button_label_NodePath = node
        self.rotation_z_button_label_NodePath.setScale(0.03)
        self.rotation_z_button_label.setFont(self.font)
        self.rotation_z_button_label_NodePath.setPos(0.9, 0, 0.2)
        
        #Display mm button text 
        self.rotation_x_button_label_degree = TextNode('Text')
        self.rotation_x_button_label_degree.setText("\N{DEGREE SIGN}") 
        node = aspect2d.attachNewNode(self.rotation_x_button_label_degree)
        self.rotation_x_button_label_degree_NodePath = node
        self.rotation_x_button_label_degree_NodePath.setScale(0.03)
        self.rotation_x_button_label_degree.setFont(self.font)
        self.rotation_x_button_label_degree_NodePath.setPos(1.5, 0, 0.4)
        
        self.rotation_y_button_label_degree = TextNode('Text')
        self.rotation_y_button_label_degree.setText("\N{DEGREE SIGN}") 
        node = aspect2d.attachNewNode(self.rotation_y_button_label_degree)
        self.rotation_y_button_label_degree_NodePath = node
        self.rotation_y_button_label_degree_NodePath.setScale(0.03)
        self.rotation_y_button_label_degree.setFont(self.font)
        self.rotation_y_button_label_degree_NodePath.setPos(1.5, 0, 0.3)
        
        self.rotation_z_button_label_degree = TextNode('Text')
        self.rotation_z_button_label_degree.setText("\N{DEGREE SIGN}") 
        node = aspect2d.attachNewNode(self.rotation_z_button_label_degree)
        self.rotation_z_button_label_degree_NodePath = node
        self.rotation_z_button_label_degree_NodePath.setScale(0.03)
        self.rotation_z_button_label_degree.setFont(self.font)
        self.rotation_z_button_label_degree_NodePath.setPos(1.5, 0, 0.2)
        
        #Display rotation value
        self.rotation_x_value = TextNode('Text')
        self.rotation_x_value.setText(f"{self.rotation_x}") 
        node = aspect2d.attachNewNode(self.rotation_x_value)
        self.rotation_x_value_NodePath = node
        self.rotation_x_value_NodePath.setScale(0.03)
        self.rotation_x_value.setFont(self.font)
        self.rotation_x_value_NodePath.setPos(1.3, 0, 0.4)
        
        self.rotation_y_value = TextNode('Text')
        self.rotation_y_value.setText(f"{self.rotation_y}") 
        node = aspect2d.attachNewNode(self.rotation_y_value)
        self.rotation_y_value_NodePath = node
        self.rotation_y_value_NodePath.setScale(0.03)
        self.rotation_y_value.setFont(self.font)
        self.rotation_y_value_NodePath.setPos(1.3, 0, 0.3)
        
        self.rotation_z_value = TextNode('Text')
        self.rotation_z_value.setText(f"{self.rotation_z}") 
        node = aspect2d.attachNewNode(self.rotation_z_value)
        self.rotation_z_value_NodePath = node
        self.rotation_z_value_NodePath.setScale(0.03)
        self.rotation_z_value.setFont(self.font)
        self.rotation_z_value_NodePath.setPos(1.3, 0, 0.2)
        
        #Info on mesh transform tab 
        #Display Mesh dimension buttons
        self.dimension_x_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                        r"\GRAPHICS\rest_text_box.png",
                                                        r"\GRAPHICS\rest_text_box.png", 
                                                        r"\GRAPHICS\rest_text_box.png"),
                                               relief = None, 
                                               scale = (0.1, 0.12, 0.03), 
                                               command = self.dimensionXButton,
                                               pos = (1.35, 0, 0.11))
        self.dimension_x_button.setTransparency(TransparencyAttrib.MAlpha)
        self.dimension_x_button.resetFrameSize()
        
        self.dimension_y_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                        r"\GRAPHICS\rest_text_box.png",
                                                        r"\GRAPHICS\rest_text_box.png", 
                                                        r"\GRAPHICS\rest_text_box.png"),
                                               relief = None, 
                                               scale = (0.1, 0.12, 0.03), 
                                               command = self.dimensionYButton,
                                               pos = (1.35, 0, 0.01))
        self.dimension_y_button.setTransparency(TransparencyAttrib.MAlpha)
        self.dimension_y_button.resetFrameSize()
        
        self.dimension_z_button = DirectButton(image = (r"\GRAPHICS\selected_text_box.png", 
                                                        r"\GRAPHICS\rest_text_box.png",
                                                        r"\GRAPHICS\rest_text_box.png", 
                                                        r"\GRAPHICS\rest_text_box.png"),
                                               relief = None, 
                                               scale = (0.1, 0.12, 0.03), 
                                               command = self.dimensionZButton,
                                               pos = (1.35, 0, -0.09))
        self.dimension_z_button.setTransparency(TransparencyAttrib.MAlpha)
        self.dimension_z_button.resetFrameSize()
        
        #Display dimension button text
        self.dimension_x_button_label = TextNode('Text')
        self.dimension_x_button_label.setText("Dimension X:") 
        node = aspect2d.attachNewNode(self.dimension_x_button_label)
        self.dimension_x_button_label_NodePath = node
        self.dimension_x_button_label_NodePath.setScale(0.03)
        self.dimension_x_button_label.setFont(self.font)
        self.dimension_x_button_label_NodePath.setPos(0.9, 0, 0.1)
        
        self.dimension_y_button_label = TextNode('Text')
        self.dimension_y_button_label.setText("Dimension Y :") 
        node = aspect2d.attachNewNode(self.dimension_y_button_label)
        self.dimension_y_button_label_NodePath = node
        self.dimension_y_button_label_NodePath.setScale(0.03)
        self.dimension_y_button_label.setFont(self.font)
        self.dimension_y_button_label_NodePath.setPos(0.9, 0, 0)
        
        self.dimension_z_button_label = TextNode('Text')
        self.dimension_z_button_label.setText("Dimension Z:") 
        node = aspect2d.attachNewNode(self.dimension_z_button_label)
        self.dimension_z_button_label_NodePath = node
        self.dimension_z_button_label_NodePath.setScale(0.03)
        self.dimension_z_button_label.setFont(self.font)
        self.dimension_z_button_label_NodePath.setPos(0.9, 0, -0.1)
        
        #Display mm button text 
        self.dimension_x_button_label_mm = TextNode('Text')
        self.dimension_x_button_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.dimension_x_button_label_mm)
        self.dimension_x_button_label_mm_NodePath = node
        self.dimension_x_button_label_mm_NodePath.setScale(0.03)
        self.dimension_x_button_label_mm.setFont(self.font)
        self.dimension_x_button_label_mm_NodePath.setPos(1.5, 0, 0.1)
        
        self.dimension_y_button_label_mm = TextNode('Text')
        self.dimension_y_button_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.dimension_y_button_label_mm)
        self.dimension_y_button_label_mm_NodePath = node
        self.dimension_y_button_label_mm_NodePath.setScale(0.03)
        self.dimension_y_button_label_mm.setFont(self.font)
        self.dimension_y_button_label_mm_NodePath.setPos(1.5, 0, 0)
        
        self.dimension_z_button_label_mm = TextNode('Text')
        self.dimension_z_button_label_mm.setText("mm") 
        node = aspect2d.attachNewNode(self.dimension_z_button_label_mm)
        self.dimension_z_button_label_mm_NodePath = node
        self.dimension_z_button_label_mm_NodePath.setScale(0.03)
        self.dimension_z_button_label_mm.setFont(self.font)
        self.dimension_z_button_label_mm_NodePath.setPos(1.5, 0, -0.1)
        
        #Display dimension value
        self.dimension_x_value = TextNode('Text')
        self.dimension_x_value.setText(f"{self.dimension_x}") 
        node = aspect2d.attachNewNode(self.dimension_x_value)
        self.dimension_x_value_NodePath = node
        self.dimension_x_value_NodePath.setScale(0.03)
        self.dimension_x_value.setFont(self.font)
        self.dimension_x_value_NodePath.setPos(1.3, 0, 0.1)
        
        self.dimension_y_value = TextNode('Text')
        self.dimension_y_value.setText(f"{self.dimension_y}") 
        node = aspect2d.attachNewNode(self.dimension_y_value)
        self.dimension_y_value_NodePath = node
        self.dimension_y_value_NodePath.setScale(0.03)
        self.dimension_y_value.setFont(self.font)
        self.dimension_y_value_NodePath.setPos(1.3, 0, 0)
        
        self.dimension_z_value = TextNode('Text')
        self.dimension_z_value.setText(f"{self.dimension_z}") 
        node = aspect2d.attachNewNode(self.dimension_z_value)
        self.dimension_z_value_NodePath = node
        self.dimension_z_value_NodePath.setScale(0.03)
        self.dimension_z_value.setFont(self.font)
        self.dimension_z_value_NodePath.setPos(1.3, 0, -0.1)
        
    def locationXButton(self) -> None:
        self.location_x_value.setText("") 
        self.location_x_entry = DirectEntry(text = "", 
                                            scale = 0.03, 
                                            command = self.setTextLocationX,
                                            numLines = 1, 
                                            entryFont = self.font,
                                            focus = 0, 
                                            relief = None, 
                                            width = 3)
        self.location_x_entry.setPos(1.3, 0, 0.7)
    
    def locationYButton(self) -> None:
        self.location_y_value.setText("") 
        self.location_y_entry = DirectEntry(text = "", 
                                            scale = 0.03, 
                                            command = self.setTextLocationY,
                                            numLines = 1, 
                                            entryFont = self.font,
                                            focus = 0, 
                                            relief = None, 
                                            width = 3)
        self.location_y_entry.setPos(1.3, 0, 0.6)
        
    def locationZButton(self) -> None:
        self.location_z_value.setText("") 
        self.location_z_entry = DirectEntry(text = "", 
                                            scale = 0.03, 
                                            command = self.setTextLocationZ,
                                            numLines = 1, 
                                            entryFont = self.font,
                                            focus = 0, 
                                            relief = None, 
                                            width = 3)
        self.location_z_entry.setPos(1.3,0,0.5)
    
    def setTextLocationX(self, textEntered:str) -> None:
        try:
            self.location_x = float(textEntered)
            self.location_x_value.setText(f"{self.location_x}") 
            self.location_x_entry.destroy()            
            self.stl.setPos(self.origin_x + self.location_x, 
                            self.origin_y + self.location_y, 
                            self.origin_z + self.location_z)
            
            pt1, pt2 = self.stl.getTightBounds()
            self.x_stl = (max(pt1[0], pt2[0]) + min(pt1[0], pt2[0])) / 2
            self.y_stl = (max(pt1[1], pt2[1]) + min(pt1[1], pt2[1])) / 2
            self.z_stl = (max(pt1[2], pt2[2]) + min(pt1[2], pt2[2])) / 2 
            self.origin.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.x_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.y_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.z_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            
            self.layer.destroy()
            self.label_radius.destroy()
            self.label_layer_count.destroy()
            self.layer_number_entry.destroy()
            self.label_layer_number.destroy()
            self.label_radius_text.destroy()
            self.label_mm.destroy()
            self.textObject.destroy()
            self.layerViewerInfo()
        except ValueError:
            pass

    def setTextLocationY(self, textEntered:str) -> None:
        try:
            self.location_y = float(textEntered)
            self.location_y_value.setText(f"{self.location_y}") 
            self.location_y_entry.destroy()
            self.stl.setPos(self.origin_x + self.location_x, 
                            self.origin_y + self.location_y, 
                            self.origin_z + self.location_z)
            
            pt1, pt2 = self.stl.getTightBounds()
            self.x_stl = (max(pt1[0], pt2[0]) + min(pt1[0], pt2[0])) / 2
            self.y_stl = (max(pt1[1], pt2[1]) + min(pt1[1], pt2[1])) / 2
            self.z_stl = (max(pt1[2], pt2[2]) + min(pt1[2], pt2[2])) / 2 
            self.origin.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.x_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.y_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.z_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            
            self.layer.destroy()
            self.label_radius.destroy()
            self.label_layer_count.destroy()
            self.layer_number_entry.destroy()
            self.label_layer_number.destroy()
            self.label_radius_text.destroy()
            self.label_mm.destroy()
            self.textObject.destroy()
            self.layerViewerInfo()
        except ValueError:
            pass
        
    def setTextLocationZ(self, textEntered:str) -> None:
        try:
            self.location_z = float(textEntered)
            self.location_z_value.setText(f"{self.location_z}") 
            self.location_z_entry.destroy()
            self.stl.setPos(self.origin_x + self.location_x, 
                            self.origin_y + self.location_y, 
                            self.origin_z + self.location_z)
            
            pt1, pt2 = self.stl.getTightBounds()
            self.x_stl = (max(pt1[0], pt2[0]) + min(pt1[0], pt2[0])) / 2
            self.y_stl = (max(pt1[1], pt2[1]) + min(pt1[1], pt2[1])) / 2
            self.z_stl = (max(pt1[2], pt2[2]) + min(pt1[2], pt2[2])) / 2 
            self.origin.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.x_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.y_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            self.z_axis.setPos(self.x_stl, self.y_stl, self.z_stl)
            
            self.layer.destroy()
            self.label_radius.destroy()
            self.label_layer_count.destroy()
            self.layer_number_entry.destroy()
            self.label_layer_number.destroy()
            self.label_radius_text.destroy()
            self.label_mm.destroy()
            self.textObject.destroy()
            self.layerViewerInfo()
        except ValueError:
            pass
        
    def rotationXButton(self) -> None:
        self.rotation_x_value.setText("") 
        self.rotation_x_entry = DirectEntry(text = "", 
                                            scale = 0.03, 
                                            command = self.setTextrotationX,
                                            numLines = 1, 
                                            entryFont = self.font,
                                            focus = 0, 
                                            relief = None, 
                                            width = 3)
        self.rotation_x_entry.setPos(1.3, 0, 0.4)
    
    def rotationYButton(self) -> None:
        self.rotation_y_value.setText("") 
        self.rotation_y_entry = DirectEntry(text = "", 
                                            scale = 0.03, 
                                            command = self.setTextrotationY,
                                            numLines = 1, 
                                            entryFont = self.font,
                                            focus = 0, 
                                            relief = None, 
                                            width = 3)
        self.rotation_y_entry.setPos(1.3, 0, 0.3)
        
    def rotationZButton(self) -> None:
        self.rotation_z_value.setText("") 
        self.rotation_z_entry = DirectEntry(text = "", 
                                            scale = 0.03, 
                                            command = self.setTextrotationZ,
                                            numLines = 1, 
                                            entryFont = self.font,
                                            focus = 0, 
                                            relief = None, 
                                            width = 3)
        self.rotation_z_entry.setPos(1.3, 0, 0.2)
    
    def setTextrotationX(self, textEntered:str) -> None:
        try:
            self.rotation_x = float(textEntered)
            self.rotation_x_value.setText(f"{self.rotation_x}") 
            self.rotation_x_entry.destroy()   
            self.stl.setP(self.original_rotation_x + self.rotation_x)
            self.layer.destroy()
            self.label_radius.destroy()
            self.label_layer_count.destroy()
            self.layer_number_entry.destroy()
            self.label_layer_number.destroy()
            self.label_radius_text.destroy()
            self.label_mm.destroy()
            self.textObject.destroy()
            self.layerViewerInfo()
        except ValueError:
            pass

    def setTextrotationY(self, textEntered:str) -> None:
        try:
            self.rotation_y = float(textEntered)
            self.rotation_y_value.setText(f"{self.rotation_y}") 
            self.rotation_y_entry.destroy()
            self.stl.setR(self.original_rotation_y + self.rotation_y)
            self.layer.destroy()
            self.label_radius.destroy()
            self.label_layer_count.destroy()
            self.layer_number_entry.destroy()
            self.label_layer_number.destroy()
            self.label_radius_text.destroy()
            self.label_mm.destroy()
            self.textObject.destroy()
            self.layerViewerInfo()
        except ValueError:
            pass
        
    def setTextrotationZ(self, textEntered:str) -> None:
        try:
            self.rotation_z = float(textEntered)
            self.rotation_z_value.setText(f"{self.rotation_z}") 
            self.rotation_z_entry.destroy()
            self.stl.setH(self.original_rotation_z + self.rotation_z)
            self.layer.destroy()
            self.label_radius.destroy()
            self.label_layer_count.destroy()
            self.layer_number_entry.destroy()
            self.label_layer_number.destroy()
            self.label_radius_text.destroy()
            self.label_mm.destroy()
            self.textObject.destroy()
            self.layerViewerInfo()
        except ValueError:
            pass
    
    def dimensionXButton(self) -> None:
        pass

    def dimensionYButton(self) -> None:
        pass
        
    def dimensionZButton(self) -> None:
        pass
    
    def parseGcode(self) -> None:
        self.done = False
        self.gcode_file_address = self.path
        self.gcode = gp.gcode_parser(self.gcode_file_address, 
                                     self.layer_height, 
                                     self.print_speed, 
                                     self.infill_percentage, 
                                     self.print_temperature,
                                     self.retraction_length, 
                                     self.retraction_speed, 
                                     self.nozzle_diameter, 
                                     self.wall_line_count, 
                                     self.start_gcode, 
                                     self.end_gcode, 
                                     self.flavor, 
                                     self.header, 
                                     self.stl_file_address, 
                                     self.location_x, 
                                     self.location_y, 
                                     self.location_z,
                                     self.rotation_x, 
                                     self.rotation_y, 
                                     self.rotation_z,
                                     self.cylinder_diameter, 
                                     self.delta_y,
                                     self.filament_diameter,
                                     self.infill_orientation)
        gcode_file = self.gcode.create_gcode()
        if str(gcode_file) != "error":
            self.gcode.write_gcode(gcode_file)
            self.loading_label.setText("The Gcode is ready!")
        else:
            self.loading_label.setText("Failed to prepare Gcode.")
        self.done = True

    
    def prepareGcodeButton(self) -> None:  
        root = Tk()
        root.withdraw()
        self.path = tkinter.filedialog.asksaveasfilename()
        root.destroy()
        if len(self.path) != 0:
            self.loading_label = TextNode('Text')
            self.loading_label.setText("Preparing Gcode...") 
            self.loading_label_NodePath = aspect2d.attachNewNode(self.loading_label)
            self.loading_label_NodePath.setScale(0.05)
            self.loading_label.setFont(self.font)
            self.loading_label_NodePath.setPos(-0.2,0, -0.55)
            t1 = threading.Thread(target = self.parseGcode)
            t1.start()
            cm = CardMaker("c")
            cm.setFrame(-100, 100, -100, 100)
            cn = pixel2d.attachNewNode(cm.generate())
            cn.setPos(950, 0, -750)
           
            vertex = """
            #version 150
            uniform mat4 p3d_ModelViewProjectionMatrix;
            uniform mat4 trans_model_to_world;
            in vec4 p3d_Vertex;
            in vec2 p3d_MultiTexCoord0;
            out vec2 texcoord;
            void main() {
                gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
                texcoord = (p3d_Vertex).xz;
            }
            """
            
            fragment = """
            #version 150
            out vec4 color;
            in vec2 texcoord;
            uniform float radiusStart;
            uniform float radiusEnd;
            uniform vec3 circleColor;
            uniform float progress;
            
            const float PI = 3.14159265359;
            void main() {
                float radius = distance(texcoord, vec2(0));
                color = vec4(0);
                if (radius > radiusStart && radius < radiusEnd) {
                   float angle = atan(texcoord.x, texcoord.y) / (2.0*PI);
                   if (angle < 0.0) angle = 1.0 + angle;
                   if (angle < progress) {
                       // Uncomment this to get a gradient
                       //color = vec4(angle*circleColor, 1);    
                       color = vec4(circleColor, 1);    
                   }
               }
            }
            """
           
            cn.setShader(Shader.make(Shader.SLGLSL, vertex, fragment))
            cn.setShaderInput("radiusStart", 30.0)
            cn.setShaderInput("radiusEnd", 35)
            counter_1 =0
            counter_2 = 0
            while not self.done:
                counter_1 += 1
                if counter_1 > 100:
                    if counter_2 == 100:
                        counter_1 = 0
                        counter_2 = 0
                    counter_2 += 1
                    cn.setShaderInput("circleColor", Vec3(1, 1, 1))
                    cn.setShaderInput("progress", counter_2 * 0.01)
                    cn.setTransparency(True)
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame()
                    time.sleep(0.01)
                else:
                    cn.setShaderInput("circleColor", Vec3(1, 1, 1))
                    cn.setShaderInput("progress", counter_1 * 0.01)
                    cn.setTransparency(True)
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame() 
                    base.graphicsEngine.renderFrame()
                    time.sleep(0.01)
            cn.setPos(950, 0, 100000)