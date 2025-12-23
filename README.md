# ⛅ Weather Forecast Scraper

A Python tool that scrapes weather forecasts and converts them into beautiful HTML reports or JSON data.

## Features

- 🌤️ Scrapes hourly weather forecasts
- 📊 Extracts temperature, humidity, wind speed, gusts, and weather conditions
- 🎨 Generates responsive, modern HTML reports
- 📱 Mobile-friendly design with interactive cards
- 📄 JSON output for programmatic use
- 🌍 Greek weather data with Greek language support

## Quick Start

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your weather URL:**
   
   Option A - Environment variable:
   ```bash
   export WEATHER_URL="https://somesomeweathersite.com/forecast/..."
   ```
   
   Option B - Command-line argument (see below)

### Usage

**Generate HTML report:**
```bash
python weather.py --html --url "https://somesomeweathersite.com/forecast/..."
```

This creates `forecast.html` with a beautiful, interactive weather forecast.

**Save to custom file:**
```bash
python weather.py --html -o my_forecast.html --url "https://somesomeweathersite.com/forecast/..."
```

**Output JSON data:**
```bash
python weather.py --url "https://somesomeweathersite.com/forecast/..."
```

## Command-Line Options

```
--html              Generate HTML report instead of JSON
-o, --output FILE   Output file path (default: forecast.html)
--url URL           Forecast URL (or use WEATHER_URL env var)
-h, --help          Show help message
```

## Output

### HTML Report
Opens in any web browser with:
- Day-by-day forecast cards
- Hourly temperature and conditions
- Wind speed and direction
- Humidity levels
- Weather condition emojis
- Responsive design (works on mobile & desktop)

### JSON Output
Structured forecast data with hourly breakdowns:
```json
[
  {
    "day": "Πεμπτη",
    "date": "4 ΔΕΚΕΜΒΡΙΟΥ",
    "hours": {
      "11:00": {
        "temperature_c": 15,
        "humidity_pct": 65,
        "wind_beaufort": 3,
        "wind_direction": "NA",
        "wind_kmh": 18,
        "gusts_kmh": 28,
        "condition": "Βροχή"
      }
    }
  }
]
```

## Example

```bash
# Set environment variable once
export WEATHER_URL="https://someweathersite.com/forecast/YOUR_LOCATION"

# Generate beautiful HTML forecast
python weather.py --html

# Or pipe to JSON for processing
python weather.py | jq '.[] | .day'
```

## Requirements

- Python 3.7+
- beautifulsoup4
- requests
- lxml

See `requirements.txt` for all dependencies.

## License

See repository for details.
