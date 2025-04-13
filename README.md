# GNSS Track Consolidation

This repository contains a Python implementation for processing GNSS track data, generating kernel density maps, reclassifying rasters, and extracting centerlines. The project uses Python libraries such as `geopandas`, `shapely`, `rasterio`, and `pygeoops`.

## Features

1. **Preprocess Shapefiles**: Split lines into individual segments.
2. **Generate Kernel Density**: Create density rasters from shapefiles.
3. **Reclassify Rasters**: Convert density rasters into binary masks.
4. **Extract Polygons**: Smooth polygon boundaries from binary rasters.
5. **Generate Centerlines**: Extract centerlines from polygons.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/OMID018/GNSS-Track-Consolidation.git
   cd GNSS-Track-Consolidation