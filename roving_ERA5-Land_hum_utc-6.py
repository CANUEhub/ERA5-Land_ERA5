import gc
import pandas as pd
import xarray as xr
import os
import numpy as np
import sys

def resample_export(dsin, rsbin="D"):
    """
    Vectorized daily resampling and export.

    Outputs:
      - t2m: daily min / mean / max
      - rh:  daily min / mean / max
      - humidex: daily min / mean / max
    """


    # ------------------------------------------------------------------
    # 2. Define daily products (vectorized)
    # ------------------------------------------------------------------
    
    print("About to give products.")
    
    for v in ["t2m","rh","humidex"]:
        
        products = {
            f"{v}": {
                "mean": dsin[f"{v}"].resample(valid_time=rsbin).mean(),
                "min":  dsin[f"{v}"].resample(valid_time=rsbin).min(),
                "max":  dsin[f"{v}"].resample(valid_time=rsbin).max(),
            }
        }
        # ------------------------------------------------------------------
        # 3. Export daily GeoTIFFs
        # ------------------------------------------------------------------
        for var, stats in products.items():
            print(f"This is the current var: {var} and stats: {stats}")
            for stat, darr in stats.items():
                #print(f"This is the current stat: {stat} and darr: {darr}")
                print(f'This is the current stat: {stat}')
                # Ensure CRS once
                if not darr.rio.crs:
                    print("NO CRS")
                    darr = darr.rio.write_crs("EPSG:4326")
    
                for t in darr.valid_time.values:
                    tstr = pd.to_datetime(t).strftime("%Y_%m_%d_%H")
                    print(f"This is the tstr for daily exports: {tstr}")
                    # CHANGE ME
                    outdir = f"/mnt/smkvol/era5-land_utc-6/{var}_daily/{stat}" #ERA5-Land
                    os.makedirs(outdir, exist_ok=True)
    
                    darr.sel(valid_time=t).rio.to_raster(
                        f"{outdir}/e5-land_utc-6_{var}_D{stat}_{tstr}.tif", # CHANGE ME
                        compress="deflate",
                        dtype="float32",
                        nodata=-9999
                    )
    
                # ----------------------------------------------------------
                # 4. Monthly mean of daily statistic (where meaningful)
                # ----------------------------------------------------------
                month_str = pd.to_datetime(darr.valid_time.values[0]).strftime("%Y_%m")
                print(f"This is the month_str for MONTHLY RESAMPLES: {month_str} ")
    
    
                # CHANGE ME
                outdir_m = f"/mnt/smkvol/era5-land_utc-6/{var}_daily_monthly/{stat}" # ERA5-Land
                os.makedirs(outdir_m, exist_ok=True)
                
                
                # MIN
                monthly_min = darr.min(dim="valid_time")
                monthly_min.rio.to_raster(
                    f"{outdir_m}/e5-land_utc-6_{var}_D{stat}_Mmin_{month_str}.tif", # ERA5-Land
                    compress="deflate",
                    dtype="float32",
                    nodata=-9999
                )
                del monthly_min
                gc.collect()
                
                # mean
                monthly_mean = darr.mean(dim="valid_time")
                monthly_mean.rio.to_raster(
                    f"{outdir_m}/e5-land_utc-6_{var}_D{stat}_Mavg_{month_str}.tif", # ERA5-Land
                    compress="deflate",
                    dtype="float32",
                    nodata=-9999
                )
                del monthly_mean
                gc.collect()
                
                # MAX
                monthly_max = darr.max(dim="valid_time")
                monthly_max.rio.to_raster(
                    f"{outdir_m}/e5-land_utc-6_{var}_D{stat}_Mmax_{month_str}.tif", # ERA5-LAND
                    compress="deflate",
                    dtype="float32",
                    nodata=-9999
                )
                del monthly_max
                gc.collect()


def get_target_month(dstm, date):
    date = pd.to_datetime(date)
    start = date.replace(day=1)
    end = start + pd.offsets.MonthEnd()
    print(f'From the GTM function, this is the start {start} and end {end} being returned.')
    print("Returning only this month: {}".format(date.month))

    return dstm.sel(valid_time = dstm.valid_time.dt.month == date.month)
    del dstm
    gc.collect()

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
    date = pd.to_datetime(date) #
    print(f"This is the date to query the loaded dataset by: {date} ")
    # CHANGE ME
    fname = file_template.format(year=date.year, month=date.month) # ERA5-Land
    print(f"This is the filename: {fname}")

    dsmg = xr.open_dataset(fname, engine="cfgrib")
#     dsmg = xr.open_dataset(
#     fname,
#     engine="cfgrib",
#     chunks={"time": 24}
# )
    
    
    print(dsmg)

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
        del dsmg
        gc.collect()

def load_target_and_adjacent_data(date, file_template):
    bounds = month_bounds(date)
    print("These are the bounds: ", bounds)

    # Load previous month
    #ds_prev = load_monthly_grib(bounds["prev_end"], file_template,target=False)

    # Load target month
    ds_target = load_monthly_grib(date, file_template)

    # Load next month
    ds_next = load_monthly_grib(bounds["next_start"], file_template,target=False)

    #combined = xr.concat([ds_prev, ds_target, ds_next], dim="time")
    #print("Concat datasets")
    combined = xr.concat([ds_target,ds_next],dim="time") # TURN ME ON WHEN YOU WANT TO CONVERT UTC TIME
    #combined = ds_target
    #return ds_target
    return combined
    gc.collect()


# CHANGE ME FOR ERA5 OR ERA5-LAND
file_template = "/mnt/smkvol/ERA5-Land_GRIB/ERA5_t2m_dewt2m_tp_HOURLY_{year}_{month:02d}/data.grib" # Master era5-land

y = int(sys.argv[1])
tm = int(sys.argv[2])


#for y in range(1983,1984):
    #for tm in range(1,13):

target_month = f"{tm:02d}"
print(f"This is the year {y} and target month: {target_month}")

combined_ds = load_target_and_adjacent_data(f"{y}-{target_month}-01", file_template)

print("Returned combine ds")
print(combined_ds.valid_time.values[0]) # FIRST VALUE
print(combined_ds.valid_time.values[-1:]) # LAST VALUE

#ds = combined_ds
print("About to begin time reassignment")
#ds = ds.reset_coords()
ds2 = combined_ds.stack(_t=("time", "step")).reset_index("_t")
ds2 = ds2.assign_coords(valid_time=("_t", ds2.valid_time.values))
ds2 = ds2.swap_dims({"_t":"valid_time"})
to_drop = [v for v in ["time", "step", "_t"] if v in ds2.variables]
ds2 = ds2.drop_vars(to_drop)
ds2 = ds2.sortby("valid_time") #

print("Converted to VALID TIME and here are the new time values: ")
print(ds2.valid_time.values[0]) # FIRST VALUE
print(ds2.valid_time.values[-1:]) # LAST VALUE

print("CONVERTING TO UTC-6")
ds2 = ds2.assign_coords(valid_time = ds2.valid_time - pd.Timedelta(hours=6)) 
# add 6 hours to change 10 AM (UTC) so it represents 10 AM (UTC-6), or 4 PM UTC
print("NEW START AND END TIMES AFTER TIMEZONE CONVERSION")
print(ds2.valid_time.values[:1]) # FIRST VALUE
print(ds2.valid_time.values[-1:]) # LAST VALUE


print("About to get just target month values and print them: ")
ds2 = get_target_month(ds2,f"{y}-{tm:02d}-01")

print("Got target month and here are the new time values: ")
print(ds2.valid_time.values[0]) # FIRST VALUE
print(ds2.valid_time.values[-1:]) # LAST VALUE

# Hourly RH
ds2['rh'] = (
    100
    * (6.112 * np.exp((17.67 * (ds2['d2m'] - 273.15)) /
                      ((ds2['d2m'] - 273.15) + 243.5)))
    / (6.112 * np.exp((17.67 * (ds2['t2m'] - 273.15)) /
                      ((ds2['t2m'] - 273.15) + 243.5)))
).clip(0,100)


print('Ran relative humidity calculation')

# Hourly Humidex
ds2['humidex'] = (
    (ds2['t2m'] - 273.15)
    + 0.5555 * (
        6.11 * np.exp(
            5417.7530 * (1 / 273.16 - 1 / ds2['d2m'])
        ) - 10
    )
)
print('Ran Humidex calculation')
# This is a test
ds2['t2m'] = ds2['t2m'] - 273.15
print('Converted temperature to celsius')

resample_export(ds2,rsbin='D') # Resample and export

del ds2, combined_ds
gc.collect()
