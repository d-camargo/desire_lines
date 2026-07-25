# Desire Lines Plugin for QGIS

The Desire Lines plugin is designed to help users create desire lines, which are visual representations of preferred or desired movement paths between points on a map. These lines are often used in urban planning, transportation studies, and spatial analysis to show the preferred or actual routes people take between locations.

## Install DesireLines

After downloading the file, open QGIS and go to the option 'Plugins -> Manage and install plugins'
![image](https://github.com/user-attachments/assets/e30e8a55-965b-4c18-8943-7e83ba1dccc1)

In the 'Plugins' window, find the option 'Install from ZIP' (1) and then locate (2) the file you downloaded from the form. Then, click on Install Plugin.

![image](https://github.com/user-attachments/assets/d1580b18-e1e3-43e5-bb0a-afe537055b9e)

During the installation process, there will be a security warning in QGIS. Click on 'Yes' to continue.

![image](https://github.com/user-attachments/assets/e1766428-7feb-4df4-bc14-8fd33d0f1eb9)

After that, QGIS will alert you that the installation has been completed. Close the Plugins window.

There are two places where you can open the plugin: (1) in the toolbar and (2) under the 'Vector' menu

![image](https://github.com/user-attachments/assets/69aaddac-a9c1-4cee-a3cb-c3fb0cbf7148)

## Features

1. **Origin/Destination Matrix**: Imports OD matrix (CSV) and traffic zone geometries to generate centroids.
2. **Desire Lines**: Generates direct desire line vectors between centroids weighted by demand.
3. **AoN (Delaunay)**: Performs All-or-Nothing traffic assignment on a synthetic Delaunay network.
4. **Highway Assignment (Alocação em rodovias)**: Performs capacity calculation (HCM 6th Edition) and traffic assignment (AoN or MSA/BPR) on real highway networks.

> **Requirements & Scope for Highway Assignment:**
> - **GISBR Plugin Requirement**: The Highway Assignment tab requires the **GISBR** plugin (`plugin_dependencies=GisBR`) to fetch official national highway network data (SNV / INDE).
> - **Highway Scope Notice**: Developed for rural and interurban highways. Urban crossings inside the network use an approximation notice and are flagged (`escopo = 'urbano'`).

Enjoy!
