import os
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from shapely.geometry import Polygon
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
import pygeoops
from shapely.geometry import LineString, MultiLineString
from Model import (
    preprocess_shapefile,
    generate_kernel_density,
    reclassify_raster,
    raster_to_smoothed_polygons,
    polygons_to_centerlines
)

CONFIG = {
    "input_shapefile": "./data/Trails_trks.shp",
    "output_directory": "./test_outputs",
    "cell_size": 0.4,
    "search_radius": 1.5,
    "tolerance": 2.5,
}

def test_model_pipeline():
    os.makedirs(CONFIG["output_directory"], exist_ok=True)

    # Step 1: Preprocess shapefile
    print("Testing: Preprocessing shapefile...")
    output_shp = preprocess_shapefile(CONFIG["input_shapefile"], CONFIG["output_directory"])
    assert os.path.exists(output_shp), "Preprocessing failed: output shapefile not created."

    # Step 2: Generate kernel density
    print("Testing: Generating kernel density...")
    density_tif = generate_kernel_density(output_shp, CONFIG["output_directory"], CONFIG["cell_size"], CONFIG["search_radius"])
    assert os.path.exists(density_tif), "Kernel density generation failed: output raster not created."

    # Step 3: Reclassify raster
    print("Testing: Reclassifying raster...")
    binary_tif = reclassify_raster(density_tif, CONFIG["output_directory"])
    assert os.path.exists(binary_tif), "Reclassification failed: binary raster not created."

    # Step 4: Raster to smoothed polygons
    print("Testing: Converting raster to smoothed polygons...")
    polygons_shp = raster_to_smoothed_polygons(binary_tif, CONFIG["output_directory"], CONFIG["tolerance"])
    assert os.path.exists(polygons_shp), "Raster to polygons conversion failed: output shapefile not created."

    # Step 5: Polygons to centerlines
    print("Testing: Extracting centerlines from polygons...")
    centerlines_shp = polygons_to_centerlines(polygons_shp, CONFIG["output_directory"])
    assert os.path.exists(centerlines_shp), "Centerlines extraction failed: output shapefile not created."

    print("All tests passed successfully!")

if __name__ == "__main__":
    test_model_pipeline()
