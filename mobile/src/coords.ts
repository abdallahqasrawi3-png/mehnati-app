export type Pin = { latitude: number; longitude: number; accuracy?: number | null };

const AR_DIGITS: Record<string, string> = { '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9', '٫': '.', '،': ',' };

function valid(lat: number, lng: number) {
  return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 && !(lat === 0 && lng === 0);
}

/**
 * Read coordinates from what people usually paste:
 *  "32.2211, 35.2544" · Google Maps links with "@lat,lng", "q=lat,lng", "query=", "ll=", or "!3dlat!4dlng".
 * Short links (maps.app.goo.gl) do not contain coordinates and return null.
 */
export function parseCoordinates(input: string): Pin | null {
  let decoded = input.trim();
  try {
    decoded = decodeURIComponent(decoded);
  } catch {
    // keep the raw text when it is not valid URI encoding
  }
  const text = decoded.replace(/[٠-٩٫،]/g, (c) => AR_DIGITS[c] ?? c);
  const num = '(-?\\d{1,3}(?:\\.\\d+)?)';
  const patterns = [
    new RegExp(`!3d${num}!4d${num}`),
    new RegExp(`@${num},\\s*${num}`),
    new RegExp(`[?&](?:q|query|ll|destination|center)=${num},\\s*${num}`),
    new RegExp(`^${num}\\s*,\\s*${num}$`),
    new RegExp(`^${num}\\s+${num}$`),
  ];
  for (const p of patterns) {
    const m = text.match(p);
    if (m) {
      const lat = Number(m[1]);
      const lng = Number(m[2]);
      if (valid(lat, lng)) return { latitude: lat, longitude: lng };
    }
  }
  return null;
}
