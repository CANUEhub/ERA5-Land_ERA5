import calendar
import cdsapi

client = cdsapi.Client()

print("CDS API works!")

s = 1983
e = 2025

def gen_ym(sy=s,ey=e):

	requests = []

	for year in range(sy,ey+1):
		for month in range(1,13):
			print(f"Downloading current year: {year} and month: {month:02d}")
			target = f"/filepath/ERA5_t2m_dewt2m_tp_HOURLY_{year}_{month:02d}.zip" # CHANGE PER VAR
 
			num_days = calendar.monthrange(year,month)[1]
			days = [f"{day:02d}" for day in range(1,num_days+1)]
			print(f'These are the days: {days}')
			#requests.append({'year':f"{year}",'month':f"{month:02d}",'day':days})
			dataset = "reanalysis-era5-land"
			request = {
				"variable": ["2m_temperature","2m_dewpoint_temperature","total_precipitation"],
				"year": [f"{year}"],
				"month": [f"{month:02d}"],
				"day": days,
				"time": [
				    "00:00", "01:00", "02:00",
				    "03:00", "04:00", "05:00",
				    "06:00", "07:00", "08:00",
				    "09:00", "10:00", "11:00",
				    "12:00", "13:00", "14:00",
				    "15:00", "16:00", "17:00",
				    "18:00", "19:00", "20:00",
				    "21:00", "22:00", "23:00"
				],
				"data_format": "grib",
				"area": [83.5, -141.5, 41.5, -52.0],
				"download_format": "zip"
			}


			client.retrieve(dataset,request,target)

gen_ym()


 