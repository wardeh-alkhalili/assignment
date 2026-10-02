import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";

const COLORS = {
  current: "#1f7a4d",
  pickup: "#1f7a4d",
  dropoff: "#9b1c1c",
  fuel: "#b45309",
  rest: "#6d28d9",
  restart: "#6d28d9",
  break: "#64748b",
};

function Fit({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (!positions.length) return;
    map.fitBounds(positions, { padding: [28, 28] });
  }, [map, positions]);
  return null;
}

export default function RouteMap({ geometry, stops }) {
  const latlngs = (geometry?.coordinates || []).map(([lng, lat]) => [lat, lng]);
  const center = latlngs[0] || [39.8, -98.5];

  return (
    <div className="card map-wrap">
      <MapContainer className="map" center={center} zoom={5} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {latlngs.length > 1 && (
          <Polyline positions={latlngs} pathOptions={{ color: "#0b1f3a", weight: 5, opacity: 0.85 }} />
        )}
        <Fit positions={latlngs} />
        {stops.map((stop, index) => (
          <CircleMarker
            key={`${stop.type}-${index}`}
            center={[stop.lat, stop.lng]}
            radius={stop.type === "current" || stop.type === "dropoff" ? 9 : 7}
            pathOptions={{
              color: "#fff",
              weight: 2,
              fillColor: COLORS[stop.type] || "#0b1f3a",
              fillOpacity: 1,
            }}
          >
            <Popup>
              <strong>{stop.title}</strong>
              <br />
              {stop.clock} — {stop.location}
              {stop.remark ? (
                <>
                  <br />
                  {stop.remark}
                </>
              ) : null}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
