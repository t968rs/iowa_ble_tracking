import pandas as pd
import geopandas as gpd
import numpy as np
from datetime import datetime, timedelta


def add_hours_to_datetime(start_date, hours):
    # Ensure the start_date is in datetime64 format
    if not isinstance(start_date, np.datetime64):
        start_date = np.datetime64(start_date)

    # Convert datetime64 to datetime
    start_datetime = pd.to_datetime(start_date)

    # Create a timedelta object with the specified hours
    time_delta = timedelta(hours=hours)

    # Calculate the end datetime
    end_datetime = start_datetime + time_delta

    # Convert back to datetime64[s]
    end_datetime64 = np.datetime64(end_datetime).astype('datetime64[s]')

    return end_datetime64


def convert_gdf_date_to_iso(gdf: gpd.GeoDataFrame, date_column: str = None) -> gpd.GeoDataFrame:
    """
    Convert date column in GeoDataFrame to ISO 8601 format for GeoJSON compatibility.

    Parameters:
    gdf (gpd.GeoDataFrame): GeoDataFrame with date column to convert.

    Returns:
    gpd.GeoDataFrame: GeoDataFrame with date column converted to ISO 8601 format.
    """
    if date_column:
        if pd.api.types.is_datetime64_any_dtype(gdf[date_column]):
            gdf[date_column] = gdf[date_column].apply(lambda x: x.isoformat() if not pd.isna(x) else None)
    else:
        for col in gdf.columns:
            if pd.api.types.is_datetime64_any_dtype(gdf[col]):
                gdf[col] = gdf[col].apply(lambda x: x.isoformat() if not pd.isna(x) else None)

    return gdf


def convert_gdf_date_to_ersi_str(gdf: gpd.GeoDataFrame, date_column) -> gpd.GeoDataFrame:
    """
    Convert date column in GeoDataFrame to ESRI-compatible format for GeoJSON compatibility.

    Parameters:
    gdf (gpd.GeoDataFrame): GeoDataFrame with date column to convert.

    Returns:
    gpd.GeoDataFrame: GeoDataFrame with date column converted to ESRI-compatible format.
    """
    gdf[date_column] = gdf[date_column].apply(lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ") if x else None)
    return gdf
