import gc
import pandas as pd
import xarray as xr
import os
import numpy as np
import sys

def get_target_month(dstm, date):
    date = pd.to_datetime(date)
    start = date.replace(day=1)
    end = start + pd.offsets.MonthEnd()

    print(f'This is the start {start} and end {end} being returned.')

    return dstm.sel(valid_time=slice(start, end))

def month_bounds(date):
    date = pd.to_datetime(date)
    # First and last day of previous month
    prev_end = (date.replace(day=1) - pd.Timedelta(days=1))
    prev_start = prev_end.replace(day=1)
    
    # First and last day of next month
    next_start = (date + pd.offsets.MonthBegin()).replace(day=1)
    next_end = next_start + pd.offsets.MonthEnd()

    return {
        "prev_start": prev_start,
        "prev_end": prev_end,
        "next_start": next_start,
        "next_end": next_end
    }

def load_monthly_grib(date, file_template,target=True):
    """
    file_template example: 'data/{year}{month:02d}.grib'
    """
    date = pd.to_datetime(date)
    fname = file_template.format(year=date.year, month=date.month)

    print(f"This is the filename: {fname}")

    dsmg = xr.open_dataset(fname, engine="cfgrib")

    if target:
        print(f"Returning ds for TARGET MONTH: {date}")
        #print(dsmg)
        return dsmg

    else:
        # Select only the requested date/time
        if "time" in dsmg:
            dsmg = dsmg.sel(time=date)
            print(f"Returning ds for DIFFERENT DATE: {date}")
            #print(dsmg)
        else:
            raise ValueError("Dataset has no 'time' coordinate to filter.")

        return dsmg

def load_target_and_adjacent_data(date, file_template):
    bounds = month_bounds(date)
    print("These are the month bounds: ", bounds)

    # Load target month
    ds_target = load_monthly_grib(date, file_template)

    print("Concat datasets")
    combined = ds_target
    return combined

file_template = "/mnt/smkvol/ERA5-Land_GRIB/ERA5_t2m_dewt2m_tp_HOURLY_{year}_{month:02d}/data.grib"

y = int(sys.argv[1])
tm = int(sys.argv[2])

# for y in range(1983,2025):
#     for tm in range(1,13):
target_month = f"{tm:02d}"
print(f"This is the year {y} and target month: {target_month}")

combined_ds = load_target_and_adjacent_data(f"{y}-{target_month}-01", file_template)

print("Returned combined ds")
print(combined_ds.valid_time.values[0]) # FIRST VALUE
print(combined_ds.valid_time.values[-1:]) # LAST VALUE

print(f'About to get target month from function for this year: {y} and this month {tm:02d}')

#ds = ds.reset_coords()
print("About to begin time stack revision")
ds2 = combined_ds.stack(_t=("time", "step")).reset_index("_t")
ds2 = ds2.assign_coords(valid_time=("_t", ds2.valid_time.values))
ds2 = ds2.swap_dims({"_t":"valid_time"})
to_drop = [v for v in ["time", "step", "_t"] if v in ds2.variables]
ds2 = ds2.drop_vars(to_drop)
ds2 = ds2.sortby("valid_time")

print("Converted to VALID TIME and here are the new time values: ")
print(ds2.valid_time.values[0]) # FIRST VALUE
print(ds2.valid_time.values[-1:]) # LAST VALUE

# Subtract by 1 day so that hour 0 becomes total for its indended day
ds2["valid_time"] = ds2.valid_time - pd.Timedelta(days=1)

print("Subtracted 24 hours and here are the new time values: ")
print(ds2.valid_time.values[0]) # FIRST VALUE
print(ds2.valid_time.values[-1:]) # LAST VALUE
ds2 = get_target_month(ds2,f"{y}-{tm:02d}-01")
print("Got target month and here are the new time values: ")
print(ds2.valid_time.values[0]) # FIRST VALUE
print(ds2.valid_time.values[-1:]) # LAST VALUE

#ds2 = ds2.chunk({"valid_time": 24, "latitude" : 100, "longitude" : 100})

# Get only 0 hour and covert to mm
ds2_daily_tp = ds2["tp"].where(ds2.valid_time.dt.hour == 0, drop=True)
ds2_daily_tp = ds2_daily_tp * 1000  # convert m → mm

print('These are the new time value: {0}'.format(ds2_daily_tp.valid_time))

for t in ds2_daily_tp.valid_time.values:
    tstr = pd.to_datetime(t).strftime("%Y_%m_%d_%H")

    print(f"Exporting this day: {tstr}")

    outdir = "/mnt/smkvol2/era5-land/tp_daily/sum"
    os.makedirs(outdir, exist_ok=True)

    ds2_daily_tp.sel(valid_time=t).rio.to_raster(
        f"{outdir}/e5-land_tp_Dsum_{tstr}.tif",
        compress="deflate",
        dtype="float32",
        nodata=-9999
    )


# ----------------------------------------------------------
# 4. Monthly mean of daily statistic (where meaningful)
# ----------------------------------------------------------
month_str = pd.to_datetime(ds2_daily_tp.valid_time.values[0]).strftime("%Y_%m")

monthly_min = ds2_daily_tp.min(dim="valid_time")
monthly_mean = ds2_daily_tp.mean(dim="valid_time")
monthly_max = ds2_daily_tp.max(dim="valid_time")
monthly_sum = ds2_daily_tp.sum(dim="valid_time")

outdir_m = "/mnt/smkvol2/era5-land/tp_daily_monthly/sum"
os.makedirs(outdir_m, exist_ok=True)

monthly_min.rio.to_raster(
    f"{outdir_m}/e5-land_tp_Dsum_Mmin_{month_str}.tif",
    compress="deflate",
    dtype="float32",
    nodata=-9999
)

monthly_mean.rio.to_raster(
    f"{outdir_m}/e5-land_tp_Dsum_Mavg_{month_str}.tif",
    compress="deflate",
    dtype="float32",
    nodata=-9999
)

monthly_max.rio.to_raster(
    f"{outdir_m}/e5-land_tp_Dsum_Mmax_{month_str}.tif",
    compress="deflate",
    dtype="float32",
    nodata=-9999
)

monthly_sum.rio.to_raster(
    f"{outdir_m}/e5-land_tp_Dsum_Msum_{month_str}.tif",
    compress="deflate",
    dtype="float32",
    nodata=-9999
)


del ds2, ds2_daily_tp, combined_ds, monthly_min, monthly_mean, monthly_max, monthly_sum
gc.collect()
