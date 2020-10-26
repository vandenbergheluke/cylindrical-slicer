# Cylindrical 3D Printer Add-on - Cylindrical Slicer 0.1.0-alpha
This is an add-on to convert a traditional Cartesian FDM 3D printer into a cylindrical 3D printer. This project involves the installation of an apparatus to replace the y-axis of the 3D printer with a rotating cylinder as well as the use of custom slicing software. By the end, you will be able to print a couple of models with a cylindrical 3D printer and slice 3D models with non-planar slicing techniques. This project was designed to work with the Anet A8 with Marlin firmware. However, this project can likely be adapted to work on other Cartesian FDM 3D Printers through a few modifications in the slicing software and the cylindrical 3D printer apparatus. The slicer was programmed from scratch in Python 3.7 using the numpy-stl library https://pypi.org/project/numpy-stl/ and the Panda3D Engine https://pypi.org/project/Panda3D/. Please read the guide found in the DOCUMENTATION folder before beginning.

## Demo Videos
https://www.youtube.com/watch?v=Pq-NW0AvSuk<br />
https://www.youtube.com/watch?v=2twj22HswTA<br />
https://www.youtube.com/watch?v=FFyrccP61u0<br />

## Contents
1. PDF guide 
      - Concepts of the cylindrical slicer
      - Cylindrical 3D printer apparatus setup
      - Slicer setup
      - Slicer navigation, controls, and features
      - Making and exporting your own compatible 3D models
      - Brief troubleshoot section
2. Assembly Drawing
      - Bill of materials
      - Parts are labeled and dimensioned
3. Cylindrical 3D Printer Apparatus
      - STL Files for printable parts of apparatus
4. Cylindrical Slicing Software
      - Cylindrically slices models and generates gcode to print the model on the cylindrical 3D printer
      - Configuration file to modify print parameters and gcodes
      - Unwrapped layer viewer to visualize the layers being printed at different radial increments 
      - 3D GUI
      - Adjustable model location and orientation
5. Printable Demo STL files 
      - Cylinder
      - Bracelet
      - Lotus
            
## PLEASE BE AWARE: 
This project has many problems. The slicer has bugs and can be quite slow. This is a project that is very early in development. It was made by a student (me) who has never done this before. USE AT YOUR OWN RISK! I did this with the intent to make something cool and I did my best to make it so you can make something cool too.
