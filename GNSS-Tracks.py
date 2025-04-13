import os
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from shapely.geometry import Polygon
from shapely.ops import linemerge, unary_union
from rasterio.transform import from_bounds
from skimage.morphology import skeletonize
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
import pygeoops  # Import pygeoops
from shapely.geometry import LineString, MultiLineString, shape as shapely_shape


def preprocess_shapefile(input_shp, output_dir):
    data = gpd.read_file(input_shp)
    if data.empty:
        raise ValueError("Input shapefile is empty or invalid.")
    single_parts = data.explode().reset_index(drop=True)
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

def generate_kernel_density(input_shp, output_dir, cell_size=0.4, search_radius=1.5):
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
        transform=from_bounds(x_min, y_min, x_max, y_max, ncols, nrows)
    ) as raster:
        rasterized = rasterize(
            [(geometry, 1) for geometry in data.geometry],
            out_shape=(nrows, ncols),
            transform=raster.transform,
            fill=0,
            all_touched=True,
            dtype='float32'
        )
        raster.write(rasterized, 1)
        smoothed = gaussian_filter(rasterized, sigma=search_radius/cell_size)
        raster.write(smoothed, 1)
    return os.path.join(output_dir, 'density.tif')

def reclassify_raster(density_tif, output_dir):
    """
    Reclassifies the density raster based on a dynamic threshold and saves the binary raster.
    """
    with rasterio.open(density_tif) as src:
        data = src.read(1)  # Read the first band of the raster

        # Visualize the original data (density map)
        plt.imshow(data, cmap='hot', interpolation='nearest')
        plt.colorbar()
        plt.title('Density of Tracks')
        plt.show()

        # Use a dynamic threshold based on the data characteristics (e.g., 88th percentile)
        threshold = np.percentile(data, 75)  # You can adjust this percentile
        binary = data > threshold  # Create a binary mask: 1 for values above threshold, 0 for below
        
        # Visualize the binary mask after thresholding
        plt.imshow(binary, cmap='gray')
        plt.title('Binary Image after Thresholding')
        plt.show()

        # Define the output binary raster file path
        binary_raster_path = os.path.join(output_dir, 'reclassified_binary.tif')

        # Save the binary mask as a new raster
        with rasterio.open(
            binary_raster_path, 'w',
            driver='GTiff', 
            height=src.height, width=src.width, 
            count=1, dtype='uint8', 
            crs=src.crs, transform=src.transform
        ) as dest:
            dest.write(binary.astype(np.uint8), 1)

        print(f"Reclassified raster saved at: {binary_raster_path}")
        return binary_raster_path


def raster_to_smoothed_polygons(binary_raster_path, output_dir, tolerance=2.5):
    """
    Converts a reclassified raster to smoothed polygons.
    """
    with rasterio.open(binary_raster_path) as src:
        labeled_array = src.read(1)
        transform = src.transform
        crs = src.crs

        # Mask to exclude 0 values
        mask = labeled_array.astype(np.uint8)

        smoothed_polygons = []
        for shape, value in shapes(labeled_array, mask=mask, transform=transform):
            if value != 0:  # Skip background values
                geom = shape["coordinates"]

                if len(geom) == 1:  # Single polygon
                    polygon = Polygon(geom[0])
                else:  # Polygon with holes
                    exterior = geom[0]
                    interiors = geom[1:]
                    polygon = Polygon(exterior, interiors)

                # Simplify polygon to smooth boundaries
                simplified_polygon = polygon.simplify(tolerance=tolerance, preserve_topology=True)
                smoothed_polygons.append(simplified_polygon)

        # Create GeoDataFrame for the smoothed polygons
        gdf_smoothed_polygons = gpd.GeoDataFrame(geometry=smoothed_polygons, crs=crs)

        # Save polygons to shapefile
        polygons_shp = os.path.join(output_dir, 'smoothed_polygons.shp')
        gdf_smoothed_polygons.to_file(polygons_shp)

        return polygons_shp
    
def split_multilines_to_segments(multilines):
    """
    Splits a MultiLineString geometry into individual LineString segments.
    """
    segments = []
    
    for multiline in multilines:
        if isinstance(multiline, MultiLineString):
            # For MultiLineString, break it into individual LineStrings using .geoms attribute
            for line in multiline.geoms:  # Access the geometries of MultiLineString
                segments.append(line)
        elif isinstance(multiline, LineString):
            # For single LineString, just add it as is
            segments.append(multiline)
    
    return segments

def polygons_to_centerlines(polygons_shp, output_dir):
    """
    Converts polygons into centerlines using pygeoops.centerline and splits any MultiLineStrings into individual segments.
    """
    gdf = gpd.read_file(polygons_shp)

    smoothed_centerlines = []
    for polygon in gdf.geometry:
        if polygon.is_valid and not polygon.is_empty:
            # Use pygeoops to calculate the centerline
            centerline = pygeoops.centerline(polygon, densify_distance=0.7, simplifytolerance=0.7)
            
            # Split any MultiLineString into individual LineString segments
            segments = split_multilines_to_segments([centerline])
            
            smoothed_centerlines.extend(segments)

    # Create GeoDataFrame for the centerlines
    gdf_smoothed_centerlines = gpd.GeoDataFrame(geometry=smoothed_centerlines, crs=gdf.crs)

    # Save centerlines to shapefile
    centerlines_shp = os.path.join(output_dir, 'smoothed_centerlines2.shp')
    gdf_smoothed_centerlines.to_file(centerlines_shp)

    return centerlines_shp

# Set up paths for input/output
input_shp = r'P:\fortech\practical_tests\Data\Site_17_19\Trails_trks.shp'
output_dir = r'P:\fortech\practical_tests\Data\Site_17_19'

# Step 1: Process Shapefile
processed_shp = preprocess_shapefile(input_shp, output_dir)

# Step 2: Generate Kernel Density Raster
density_tif = generate_kernel_density(processed_shp, output_dir)

# Step 3: Reclassify the Raster (Binary)
binary_raster_path = reclassify_raster(density_tif, output_dir)

# Step 4: Convert Binary Raster to Polygons (Smoothed)
polygons_shp = raster_to_smoothed_polygons(binary_raster_path, output_dir)

# Step 5: Convert Polygons to Centerlines (Split into individual segments)
centerlines_shp = polygons_to_centerlines(polygons_shp, output_dir)

# Print results
print(f"Generated smoothed polygons shapefile: {polygons_shp}")
print(f"Generated smoothed centerlines shapefile: {centerlines_shp}")
