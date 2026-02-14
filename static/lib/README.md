# Leaflet.js Bundle

This directory should contain Leaflet 1.9+ files:
- leaflet.js
- leaflet.css
- marker-icon.png
- marker-icon-2x.png
- marker-shadow.png

## Download Instructions

Download Leaflet 1.9.4 from:
https://leafletjs.com/download.html

Or use unpkg CDN links to download:
```bash
curl -sL https://unpkg.com/leaflet@1.9.4/dist/leaflet.js -o leaflet.js
curl -sL https://unpkg.com/leaflet@1.9.4/dist/leaflet.css -o leaflet.css
curl -sL https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png -o marker-icon.png
curl -sL https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png -o marker-icon-2x.png
curl -sL https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png -o marker-shadow.png
```

## Temporary CDN Fallback

For development, the application will fall back to CDN if local files are not available.
