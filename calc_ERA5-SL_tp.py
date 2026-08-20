import gc
import pandas as pd
import xarray as xr
import numpy as np
import os


for y in range(1983,2025):

    ds = xr.open_dataset(f"/mnt/smkvol/ERA5-SL_GRIB/ERA5-sl_tp_HOURLY_{y}/data.grib", engine="cfgrib")
    
    for tm in range(1,13):
        target_month = f"{tm:02d}"
        print(f"This is the year {y} and target month: {target_month}")
        
        date = pd.to_datetime(f"{y}-{target_month}")
        start = date.replace(day=1)
        end = start + pd.offsets.MonthEnd()

        print(f'From the GTM function, this is the start {start} and end {end} being returned.')
        print("These are start and end time stamps")
        print(ds.time.values[0]) # FIRST VALUE
        print(ds.time.values[-1:]) # LAST VALUE

        print("About to begin time reassignmet")
        #ds = ds.reset_coords()

        ds2 = ds.stack(_t=("time", "step")).reset_index("_t")
        ds2 = ds2.assign_coords(valid_time=("_t", ds2.valid_time.values))
        ds2 = ds2.swap_dims({"_t":"valid_time"})
        to_drop = [v for v in ["time", "step", "_t"] if v in ds2.variables]
        ds2 = ds2.drop_vars(to_drop)
        ds2 = ds2.sortby("valid_time")
        
        dup_count = ds2.valid_time.to_series().duplicated().sum()
        print("HERE ARE THE DUP COUNTS: ", dup_count)
        
        ds2 = ds2["tp"].clip(min=0).fillna(0) * 1000 # Convert to mm and clip to 0 for anomolies

        print("Converted to valid_time and here are the new time values: ")
        print(ds2.valid_time.values[0]) # FIRST VALUE
        print(ds2.valid_time.values[-1:]) # LAST VALUE

        # Select ymonth
        ds_ymonth = ds2.sel(valid_time=slice(start, end))
        
        print("Selected only this month: ")
        print(ds2.valid_time.values[0]) # FIRST VALUE
        print(ds2.valid_time.values[-1:]) # LAST VALUE
        
        ds_ymonth_day = ds_ymonth.resample(valid_time="D").sum()
        
        print("Just resampled to day")
        print(ds2.valid_time.values[0]) # FIRST VALUE
        print(ds2.valid_time.values[-1:]) # LAST VALUE
             
        for t in ds_ymonth_day.valid_time.values:
            tstr = pd.to_datetime(t).strftime("%Y_%m_%d_%H")
            print("Exporting daily sum for: ",tstr)
        
            outdir = "/mnt/smkvol/era5-sl/tp_daily/sum"
            os.makedirs(outdir, exist_ok=True)
        
            ds_ymonth_day.sel(valid_time=t).rio.to_raster(
                f"{outdir}/e5-sl_tp_Dsum_{tstr}.tif",
                compress="deflate",
                dtype="float32",
                nodata=-9999
            )
        
        
        # ----------------------------------------------------------
        # 4. Monthly mean of daily statistic (where meaningful)
        # ----------------------------------------------------------
        month_str = pd.to_datetime(ds_ymonth_day.valid_time.values[0]).strftime("%Y_%m")
        print("This is the month string: ", month_str)
        
        monthly_min = ds_ymonth_day.min(dim="valid_time")
        monthly_mean = ds_ymonth_day.mean(dim="valid_time")
        monthly_max = ds_ymonth_day.max(dim="valid_time")
        monthly_sum = ds_ymonth_day.sum(dim="valid_time")
        
        outdir_m = "/mnt/smkvol/era5-sl/tp_daily_monthly/sum"
        os.makedirs(outdir_m, exist_ok=True)
        
        monthly_min.rio.to_raster(
            f"{outdir_m}/e5-sl_tp_Dsum_Mmin_{month_str}.tif",
            compress="deflate",
            dtype="float32",
            nodata=-9999
        )
        monthly_mean.rio.to_raster(
            f"{outdir_m}/e5-sl_tp_Dsum_Mavg_{month_str}.tif",
            compress="deflate",
            dtype="float32",
            nodata=-9999
        )
        monthly_max.rio.to_raster(
            f"{outdir_m}/e5-sl_tp_Dsum_Mmax_{month_str}.tif",
            compress="deflate",
            dtype="float32",
            nodata=-9999
        )
        
        monthly_sum.rio.to_raster(
            f"{outdir_m}/e5-sl_tp_Dsum_Msum_{month_str}.tif",

            compress="deflate",
            dtype="float32",
            nodata=-9999
        )

        del ds2,ds_ymonth,ds_ymonth_day
        gc.collect()
