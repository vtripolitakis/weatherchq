import os
import re
import json
import argparse
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

import requests
from bs4 import BeautifulSoup


@dataclass
class ForecastEntry:
    day_name: str
    date: str              # "4 ΔΕΚΕΜΒΡΙΟΥ"
    time: str              # "11:00"
    temperature_c: Optional[int]
    humidity_pct: Optional[int]
    wind_beaufort: Optional[int]
    wind_direction: Optional[str]
    wind_kmh: Optional[int]
    gusts_kmh: Optional[int]
    condition: Optional[str]


def parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r'-?\d+', text)
    return int(m.group()) if m else None


def scrape_forecast(html: str) -> List[ForecastEntry]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[ForecastEntry] = []

    # Κάθε "μπλοκ ημέρας" ξεκινά με td.forecastDate
    for date_cell in soup.select("td.forecastDate"):
        # Πάρε όνομα ημέρας + ημερομηνία
        flleft = date_cell.find("div", class_="flleft")
        if not flleft:
            continue

        # Πρώτο text node = όνομα ημέρας (π.χ. "Πεμπτη ")
        day_name = flleft.contents[0].strip()

        day_number_span = flleft.find("span", class_="dayNumbercf")
        if not day_number_span:
            continue

        # Το dayNumbercf έχει: "4" + <span class="monthNumbercf">ΔΕΚΕΜΒΡΙΟΥ</span>
        # Το πρώτο child είναι ο αριθμός
        day_number = ""
        for child in day_number_span.contents:
            if isinstance(child, str):
                day_number = child.strip()
                break

        month_span = day_number_span.find("span", class_="monthNumbercf")
        month_name = month_span.get_text(strip=True) if month_span else ""

        date_str = f"{day_number} {month_name}".strip()

        # Τώρα πάμε στις επόμενες σειρές μέχρι να βρούμε την επόμενη forecastDate
        day_row = date_cell.parent  # <tr> που περιέχει το forecastDate
        for row in day_row.find_next_siblings("tr"):
            # Σταματάμε όταν εμφανιστεί νέα μέρα
            if row.find("td", class_="forecastDate"):
                break

            if "perhour" not in (row.get("class") or []):
                continue

            # Ώρα
            time_cell = row.select_one("td.fulltime td")
            time_text = time_cell.get_text(strip=True) if time_cell else None

            # Θερμοκρασία
            temp_div = row.select_one("td.temperature .tempcolorcell")
            temp_c = None
            if temp_div:
                temp_c = parse_int(temp_div.get_text(" ", strip=True))

            # Υγρασία
            hum_cell = row.select_one("td .humidity")
            hum_pct = None
            if hum_cell:
                hum_pct = parse_int(hum_cell.get_text(" ", strip=True))

            # Άνεμος (Μπφ, κατεύθυνση, km/h)
            wind_main_td = row.select_one("td.anemosfull table tr td")
            wind_beaufort = wind_dir = None
            wind_kmh = None
            if wind_main_td:
                wind_text = " ".join(wind_main_td.stripped_strings)
                # π.χ. "5 Μπφ NA   35 Km/h"
                m_bf = re.search(r"(\d+)\s*Μπφ\s*([A-ZΑ-Ω]+)", wind_text)
                if m_bf:
                    wind_beaufort = int(m_bf.group(1))
                    wind_dir = m_bf.group(2)

                m_kmh = re.search(r"(\d+)\s*Km/h", wind_text)
                if m_kmh:
                    wind_kmh = int(m_kmh.group(1))

            # Ριπές
            gust_td = row.select_one("td.ripesyellowcenter")
            gusts_kmh = None
            if gust_td:
                gusts_kmh = parse_int(gust_td.get_text(" ", strip=True))

            # Καιρικό φαινόμενο
            cond_cell = row.select_one("td.PhenomenaSpecialTableCell .phenomeno-name")
            condition = None
            if cond_cell:
                # Αφαιρούμε τα [xx-yy] αν υπάρχουν
                cond_text = cond_cell.get_text(" ", strip=True)
                condition = cond_text.split("[")[0].strip()

            entry = ForecastEntry(
                day_name=day_name,
                date=date_str,
                time=time_text,
                temperature_c=temp_c,
                humidity_pct=hum_pct,
                wind_beaufort=wind_beaufort,
                wind_direction=wind_dir,
                wind_kmh=wind_kmh,
                gusts_kmh=gusts_kmh,
                condition=condition,
            )
            results.append(entry)

    return results


def group_by_day(entries: List[ForecastEntry]):
    grouped = {}

    for entry in entries:
        key = f"{entry.day_name} {entry.date}"

        if key not in grouped:
            grouped[key] = {
                "day": entry.day_name,
                "date": entry.date,
                "hours": {}
            }

        grouped[key]["hours"][entry.time] = {
            "temperature_c": entry.temperature_c,
            "humidity_pct": entry.humidity_pct,
            "wind_beaufort": entry.wind_beaufort,
            "wind_direction": entry.wind_direction,
            "wind_kmh": entry.wind_kmh,
            "gusts_kmh": entry.gusts_kmh,
            "condition": entry.condition,
        }

    # Θέλουμε λίστα, όχι dict
    return list(grouped.values())


def get_weather_emoji(condition: Optional[str]) -> str:
    """Return an emoji based on the weather condition."""
    if not condition:
        return "🌡️"
    cond = condition.upper()
    if "ΚΑΤΑΙΓΙΔΑ" in cond:
        return "⛈️"
    if "ΒΡΟΧΗ" in cond:
        return "🌧️"
    if "ΧΙΟΝΙ" in cond:
        return "❄️"
    if "ΣΥΝΝΕΦ" in cond:
        return "☁️"
    if "ΑΡΑΙΗ" in cond or "ΛΙΓΑ" in cond:
        return "🌤️"
    if "ΗΛΙΟΦΑΝΕΙΑ" in cond or "ΑΙΘΡΙΟΣ" in cond:
        return "☀️"
    return "🌡️"


def render_html(grouped_days) -> str:
    # Modern, responsive HTML with emojis
    parts = [
        "<!DOCTYPE html>",
        "<html lang='el'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "<title>🌤️ Πρόγνωση Καιρού</title>",
        "<style>",
        "* { box-sizing: border-box; }",
        "body { ",
        "  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;",
        "  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);",
        "  min-height: 100vh;",
        "  color: #111827;",
        "  margin: 0;",
        "  padding: 1rem;",
        "}",
        ".container { max-width: 1200px; margin: 0 auto; }",
        "h1 {",
        "  text-align: center;",
        "  margin-bottom: 2rem;",
        "  color: #ffffff;",
        "  font-size: 2.5rem;",
        "  text-shadow: 2px 2px 4px rgba(0,0,0,0.2);",
        "}",
        ".day-card {",
        "  background: rgba(255,255,255,0.95);",
        "  border-radius: 20px;",
        "  padding: 1.5rem;",
        "  box-shadow: 0 20px 40px rgba(0,0,0,0.15);",
        "  margin-bottom: 1.5rem;",
        "  backdrop-filter: blur(10px);",
        "  transition: transform 0.3s ease, box-shadow 0.3s ease;",
        "}",
        ".day-card:hover {",
        "  transform: translateY(-5px);",
        "  box-shadow: 0 25px 50px rgba(0,0,0,0.2);",
        "}",
        ".day-title {",
        "  font-size: 1.4rem;",
        "  font-weight: 700;",
        "  margin-bottom: 1rem;",
        "  display: flex;",
        "  justify-content: space-between;",
        "  align-items: center;",
        "  flex-wrap: wrap;",
        "  gap: 0.5rem;",
        "  padding-bottom: 1rem;",
        "  border-bottom: 2px solid #e5e7eb;",
        "}",
        ".day-title .day-name { color: #4f46e5; }",
        ".day-title .date {",
        "  background: linear-gradient(135deg, #667eea, #764ba2);",
        "  color: white;",
        "  padding: 0.4rem 1rem;",
        "  border-radius: 20px;",
        "  font-size: 0.9rem;",
        "}",
        ".table-wrapper { overflow-x: auto; -webkit-overflow-scrolling: touch; }",
        "table { width: 100%; border-collapse: collapse; min-width: 600px; }",
        "th, td { padding: 0.75rem 0.5rem; text-align: center; font-size: 0.9rem; }",
        "th {",
        "  border-bottom: 2px solid #e5e7eb;",
        "  background: linear-gradient(135deg, #f3f4f6, #e5e7eb);",
        "  font-weight: 600;",
        "  color: #374151;",
        "  white-space: nowrap;",
        "}",
        "tbody tr { transition: background-color 0.2s ease; }",
        "tbody tr:nth-child(even) { background: #f9fafb; }",
        "tbody tr:nth-child(odd) { background: #ffffff; }",
        "tbody tr:hover { background: #eef2ff; }",
        ".condition { text-align: left; font-weight: 500; }",
        ".temp { font-weight: 700; color: #dc2626; }",
        ".humidity { color: #0891b2; }",
        ".wind { color: #059669; }",
        "@media (max-width: 768px) {",
        "  body { padding: 0.5rem; }",
        "  h1 { font-size: 1.8rem; margin-bottom: 1rem; }",
        "  .day-card { padding: 1rem; border-radius: 15px; }",
        "  .day-title { font-size: 1.1rem; }",
        "  th, td { padding: 0.5rem 0.3rem; font-size: 0.8rem; }",
        "}",
        "@media (max-width: 480px) {",
        "  h1 { font-size: 1.5rem; }",
        "  .day-title { flex-direction: column; text-align: center; }",
        "  .day-title .date { margin-top: 0.5rem; }",
        "}",
        "</style>",
        "</head>",
        "<body>",
        "<div class='container'>",
        "<h1>⛅ Πρόγνωση ανά 3ωρο 🌡️</h1>",
    ]

    for day in grouped_days:
        parts.append("<section class='day-card'>")
        parts.append(
            f"<div class='day-title'>"
            f"<span class='day-name'>📅 {day['day']}</span>"
            f"<span class='date'>{day['date']}</span></div>"
        )
        parts.append("<div class='table-wrapper'>")
        parts.append("<table>")
        parts.append(
            "<thead><tr>"
            "<th>🕐 Ώρα</th>"
            "<th>🌡️ °C</th>"
            "<th>💧 %</th>"
            "<th>💨 Μπφ/κατ.</th>"
            "<th>🌬️ Km/h</th>"
            "<th>🌪️ Ριπές</th>"
            "<th class='condition'>☁️ Φαινόμενο</th>"
            "</tr></thead>"
        )
        parts.append("<tbody>")
        for hour in sorted(day["hours"].keys()):
            h = day["hours"][hour]
            wind = ""
            if h["wind_beaufort"] is not None or h["wind_direction"]:
                wind = f"{h['wind_beaufort'] or ''} {h['wind_direction'] or ''}".strip()
            
            weather_emoji = get_weather_emoji(h['condition'])
            temp_display = f"{h['temperature_c']}°" if h['temperature_c'] is not None else '-'
            
            parts.append(
                "<tr>"
                f"<td><strong>{hour}</strong></td>"
                f"<td class='temp'>{temp_display}</td>"
                f"<td class='humidity'>{h['humidity_pct'] if h['humidity_pct'] is not None else '-'}</td>"
                f"<td class='wind'>{wind or '-'}</td>"
                f"<td>{h['wind_kmh'] if h['wind_kmh'] is not None else '-'}</td>"
                f"<td>{h['gusts_kmh'] if h['gusts_kmh'] is not None else '-'}</td>"
                f"<td class='condition'>{weather_emoji} {h['condition'] or '-'}</td>"
                "</tr>"
            )
        parts.append("</tbody></table></div></section>")

    parts.append("</div>")
    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape forecast from meteo.gr and output JSON or HTML."
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Output a beautiful HTML file instead of JSON",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file path (default: forecast.html when using --html)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=os.environ.get("WEATHER_URL"),
        help="Meteo URL to scrape (or set WEATHER_URL env var)",
    )

    args = parser.parse_args()

    if not args.url:
        parser.error("URL is required: use --url or set WEATHER_URL env var")

    html = requests.get(args.url).text
    entries = scrape_forecast(html)
    grouped_days = group_by_day(entries)

    if args.html:
        out_path = Path(args.output or "forecast.html")
        out_path.write_text(render_html(grouped_days), encoding="utf-8")
        print(f"HTML forecast written to: {out_path.resolve()}")
    else:
        print(json.dumps(grouped_days, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
