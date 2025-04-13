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

# Configuration
CONFIG = {
    "input_shapefile": "./data/Trails_trks.shp",
    "output_directory": "./tests",
    "cell_size": 0.4,
    "search_radius": 1.5,
    "tolerance": 2.5,
}

def preprocess_shapefile(input_shp, output_dir):
    """Splits lines in a shapefile into individual segments."""
    data = gpd.read_file(input_shp)
    if data.empty:
        raise ValueError("Input shapefile is empty or invalid.")
    single_parts = data.explode(index_parts=False).reset_index(drop=True)
    split_lines = []
    for _, row in single_parts.iterrows():
        line = row.geometry
        if line.geom_type == 'LineString':
            for i in range(len(line.coords) - 1):
                point_start, point_end = line.coords[i], line.coords[i+1]
                split_lines.append(LineString([point_start, point_end]))
    split_lines_gdf = gpd.GeoDataFrame({'geometry': split_lines}, crs=single_parts.crs)
    split_lines_shp = os.path.join(output_dir, 'split_lines.shp')
    split_lines_gdf.to_file(split_lines_shp)
    return split_lines_shp

def generate_kernel_density(input_shp, output_dir, cell_size, search_radius):
    """Generates a kernel density raster from shapefiles."""
    data = gpd.read_file(input_shp)
    if data.empty:
        raise ValueError("Processed shapefile is empty or invalid.")
    x_min, y_min, x_max, y_max = data.total_bounds
    ncols, nrows = int((x_max - x_min) / cell_size), int((y_max - y_min) / cell_size)
    with rasterio.open(
        os.path.join(output_dir, 'density.tif'), 'w',
        driver='GTiff',
        height=nrows, width=ncols,
        count=1, dtype='float32',
        crs=data.crs,
        transform=rasterio.transform.from_bounds(x_min, y_min, x_max, y_max, ncols, nrows)
    ) as raster:
        rasterized = rasterize(
            [(geometry, 1) for geometry in data.geometry],
            out_shape=(nrows, ncols),
            transform=raster.transform,
            fill=0,
            all_touched=True,
            dtype='float32'
        )
        smoothed = gaussian_filter(rasterized, sigma=search_radius/cell_size)
        raster.write(smoothed, 1)
    return os.path.join(output_dir, 'density.tif')

def reclassify_raster(density_tif, output_dir):
    """Reclassifies the density raster into a binary mask."""
    with rasterio.open(density_tif) as src:
        data = src.read(1)
        threshold = np.percentile(data, 75)
        binary = data > threshold
        binary_raster_path = os.path.join(output_dir, 'reclassified_binary.tif')
        with rasterio.open(
            binary_raster_path, 'w',
            driver='GTiff',
            height=src.height, width=src.width,
            count=1, dtype='uint8',
            crs=src.crs, transform=src.transform
        ) as dest:
            dest.write(binary.astype(np.uint8), 1)
    return binary_raster_path

def raster_to_smoothed_polygons(binary_raster_path, output_dir, tolerance):
    """Converts a binary raster into smoothed polygons."""
    with rasterio.open(binary_raster_path) as src:
        labeled_array = src.read(1)
        mask = labeled_array.astype(np.uint8)
        smoothed_polygons = []
        for shape, value in shapes(labeled_array, mask=mask, transform=src.transform):
            if value != 0:
                polygon = Polygon(shape["coordinates"][0])
                simplified_polygon = polygon.simplify(tolerance, preserve_topology=True)
                smoothed_polygons.append(simplified_polygon)
        gdf_smoothed_polygons = gpd.GeoDataFrame(geometry=smoothed_polygons, crs=src.crs)
        polygons_shp = os.path.join(output_dir, 'smoothed_polygons.shp')
        gdf_smoothed_polygons.to_file(polygons_shp)
    return polygons_shp

def polygons_to_centerlines(polygons_shp, output_dir):
    """Extracts centerlines from polygons using pygeoops."""
    gdf = gpd.read_file(polygons_shp)
    smoothed_centerlines = []
    for polygon in gdf.geometry:
        if polygon.is_valid and not polygon.is_empty:
            centerline = pygeoops.centerline(polygon, densify_distance=0.7, simplifytolerance=0.7)
            if isinstance(centerline, MultiLineString):
                smoothed_centerlines.extend(centerline.geoms)
            elif isinstance(centerline, LineString):
                smoothed_centerlines.append(centerline)
    gdf_smoothed_centerlines = gpd.GeoDataFrame(geometry=smoothed_centerlines, crs=gdf.crs)
    centerlines_shp = os.path.join(output_dir, 'smoothed_centerlines.shp')
    gdf_smoothed_centerlines.to_file(centerlines_shp)
    return centerlines_shp

# Main Execution
if __name__ == "__main__":
    input_shp = CONFIG["input_shapefile"]
    output_dir = CONFIG["output_directory"]
    cell_size = CONFIG["cell_size"]
    search_radius = CONFIG["search_radius"]
    tolerance = CONFIG["tolerance"]

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print("Processing shapefile...")
    split_lines_shp = preprocess_shapefile(input_shp, output_dir)

    print("Generating kernel density...")
    density_tif = generate_kernel_density(split_lines_shp, output_dir, cell_size, search_radius)

    print("Reclassifying raster...")
    binary_raster_path = reclassify_raster(density_tif, output_dir)

    print("Converting raster to polygons...")
    polygons_shp = raster_to_smoothed_polygons(binary_raster_path, output_dir, tolerance)

    print("Extracting centerlines from polygons...")
    centerlines_shp = polygons_to_centerlines(polygons_shp, output_dir)

    print(f"Smoothed polygons saved at: {polygons_shp}")
    print(f"Smoothed centerlines saved at: {centerlines_shp}")
