# GNSS Track Consolidation

This repository contains a Python implementation for processing GNSS track data, generating kernel density maps, reclassifying rasters, and extracting centerlines. The project uses Python libraries such as `geopandas`, `shapely`, `rasterio`, and `pygeoops`.

## Features

1. **Preprocess Shapefiles**: Split lines into individual segments.
2. **Generate Kernel Density**: Create density rasters from shapefiles.
3. **Reclassify Rasters**: Convert density rasters into binary masks.
4. **Extract Polygons**: Smooth polygon boundaries from binary rasters.
5. **Generate Centerlines**: Extract centerlines from polygons.
<img width="781" height="312" alt="image" src="https://github.com/user-attachments/assets/bcaa6223-ceb3-44d2-b0f3-d2fb60782750" />

## Publication
You can read the details in published paper here https://doi.org/10.1016/j.atech.2025.101038
Citation: Cao, S., Abdi, O., Koivukoski, K., Mao, Z., & Uusitalo, J. (2025). Automating the consolidation of GNSS logging tracks and machine pass counting in Boreal forests. Smart Agricultural Technology, 101038.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/OMID018/GNSS-Track-Consolidation.git
   cd GNSS-Track-Consolidation
