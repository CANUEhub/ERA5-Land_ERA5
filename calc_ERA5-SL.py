import gc
import pandas as pd
import xarray as xr
import numpy as np
import os

def resample_export(dsin, rsbin="D"):


    # ------------------------------------------------------------------
    # 2. Define daily products (vectorized)
    # ------------------------------------------------------------------
    
    print("About to give products.")
    products = {
        "t2m": {
            "mean": dsin["t2m"].resample(time=rsbin).mean(),
            "min":  dsin["t2m"].resample(time=rsbin).min(),
            "max":  dsin["t2m"].resample(time=rsbin).max(),
        },
        "rh": {
            "mean": dsin["rh"].resample(time=rsbin).mean(),
            "min":  dsin["rh"].resample(time=rsbin).min(),
            "max":  dsin["rh"].resample(time=rsbin).max(),
        },
        "humidex": {
            "mean": dsin["humidex"].resample(time=rsbin).mean(),
            "min": dsin["humidex"].resample(time=rsbin).min(),
            "max": dsin["humidex"].resample(time=rsbin).max()
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

            for t in darr.time.values:
                tstr = pd.to_datetime(t).strftime("%Y_%m_%d_%H")
                print(f"This is the tstr for daily exports: {tstr}")

                outdir = f"/mnt/smkvol/era5-sl/{var}_daily/{stat}" # ERA5 single levels
                os.makedirs(outdir, exist_ok=True)

                darr.sel(time=t).rio.to_raster(
                    f"{outdir}/e5-sl_{var}_D{stat}_{tstr}.tif",
                    compress="deflate",
                    dtype="float32",
                    nodata=-9999
                )

            # ----------------------------------------------------------
            # 4. Monthly mean of daily statistic (where meaningful)
            # ----------------------------------------------------------
            month_str = pd.to_datetime(darr.time.values[0]).strftime("%Y_%m")
            print(f"This is the month_str for MONTHLY RESAMPLES: {month_str} ")


            monthly_min  = darr.resample(time="1M").min()
            monthly_mean = darr.resample(time="1M").mean()
            monthly_max  = darr.resample(time="1M").max()


            outdir_m = f"/mnt/smkvol/era5-sl/{var}_daily_monthly/{stat}" # ERA5 single levels
            os.makedirs(outdir_m, exist_ok=True)


            print(f"THIS IS THE MONTH STRING: {month_str}")
            
            monthly_min.isel(time=0).rio.to_raster(
                f"{outdir_m}/e5-sl_{var}_D{stat}_Mmin_{month_str}.tif",
                compress="deflate",
                dtype="float32",
                nodata=-9999
            )
            monthly_mean.isel(time=0).rio.to_raster(
                f"{outdir_m}/e5-sl_{var}_D{stat}_Mavg_{month_str}.tif",
                compress="deflate",
                dtype="float32",
                nodata=-9999
            )
            monthly_max.isel(time=0).rio.to_raster(
                f"{outdir_m}/e5-sl_{var}_D{stat}_Mmax_{month_str}.tif",
                compress="deflate",
                dtype="float32",
                nodata=-9999
            )



for y in range(1983,2025):

    ds = xr.open_dataset(rf"/mnt/smkvol/ERA5-SL_GRIB/ERA5-sl_t2m_dewt2m_HOURLY_{y}/data.grib", engine="cfgrib")
    
    for tm in range(1,13):
        target_month = f"{tm:02d}"
        print(f"This is the year {y} and target month: {target_month}")
        
        date = pd.to_datetime(f"{y}-{target_month}")
        start = date.replace(day=1)
        end = start + pd.offsets.MonthEnd()

        print(f'From the GTM function, this is the start {start} and end {end} being returned.')

        print("Existing timestamps ")
        print(ds.time.values[0]) # FIRST VALUE
        print(ds.time.values[-1:]) # LAST VALUE

        # Select ymonth
        ds_ymonth = ds.sel(time=slice(start, end))
        
        print("Returned dsymonth: ")
        print(ds_ymonth.time.values[0]) # FIRST VALUE
        print(ds_ymonth.time.values[-1:]) # LAST VALUE
        
        ds_ymonth['rh'] = (
                    100
                    * (6.112 * np.exp((17.67 * (ds_ymonth['d2m'] - 273.15)) /
                                      ((ds_ymonth['d2m'] - 273.15) + 243.5)))
                    / (6.112 * np.exp((17.67 * (ds['t2m'] - 273.15)) /
                                      ((ds_ymonth['t2m'] - 273.15) + 243.5)))
                ).clip(0,100)


        print('Ran relative humidity calculation')

        ds_ymonth['humidex'] = (
                    (ds_ymonth['t2m'] - 273.15)
                    + 0.5555 * (
                        6.11 * np.exp(
                            5417.7530 * (1 / 273.16 - 1 / ds_ymonth['d2m'])
                        ) - 10
                    )
                )
        print('Ran humidex calculation')
        ds_ymonth['t2m'] = ds_ymonth['t2m'] - 273.15
        print('Converted temperature to celsius')

        resample_export(ds_ymonth,rsbin='D')
        
        del ds_ymonth
        gc.collect()


# daily_mean = ds.resample(time="1D").mean()
# daily_min  = ds.resample(time="1D").min()
# daily_max  = ds.resample(time="1D").max()

# # %% 
# # MONTHLY
# ds_dmean_mon_mean = daily_mean.resample(time="MS").mean()
# ds_dmean_mon_min = daily_mean.resample(time="MS").min()
# ds_dmean_mon_max = daily_mean.resample(time="MS").max()

# ds_dmin_mon_mean = daily_min.resample(time="MS").mean()
# ds_dmin_mon_min = daily_min.resample(time="MS").min()
# ds_dmin_mon_max = daily_min.resample(time="MS").max()

# ds_dmax_mon_mean = daily_max.resample(time="MS").mean()
# ds_dmax_mon_min = daily_max.resample(time="MS").min()
# ds_dmax_mon_max = daily_max.resample(time="MS").max()

