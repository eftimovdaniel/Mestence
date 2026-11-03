import { useEffect, useState } from "react";
import { MapContainer, Marker, Polyline, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";

const STIP = [41.745, 22.193];

function ago(iso, now) {
  if (!iso) return "";
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `пред ${seconds} секунди`;
  return `пред ${Math.round(seconds / 60)} мин`;
}

function kindOf(parking) {
  if (parking.free_spots == null) return "unknown";
  if (parking.free_spots === 0) return "full";
  return "free";
}

function statusText(parking) {
  const kind = kindOf(parking);
  if (kind === "unknown") return "Нема податок";
  if (kind === "full") return "Нема место";
  return `${parking.free_spots} слободни`;
}

function pinIcon(kind, active) {
  const size = active ? 42 : 34;
  return L.divIcon({
    className: "pin-wrap",
    html: `<span class="marker marker-${kind}${active ? " is-active" : ""}"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size - 4],
  });
}

function RouteLine({ route }) {
  const map = useMap();

  useEffect(() => {
    if (!route?.length) return;
    map.fitBounds(route, {
      paddingTopLeft: [30, 90],
      paddingBottomRight: [30, 240],
    });
  }, [route, map]);

  if (!route?.length) return null;
  return (
    <>
      <Polyline
        positions={route}
        pathOptions={{ color: "#ffffff", weight: 10, opacity: 1, lineCap: "round", lineJoin: "round" }}
      />
      <Polyline
        positions={route}
        pathOptions={{ color: "#1f6b3a", weight: 6, opacity: 1, lineCap: "round", lineJoin: "round" }}
      />
    </>
  );
}

const meIcon = L.divIcon({
  className: "pin-wrap",
  html: `<span class="pin pin-me"></span>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

function MapFocus({ focus, parking, me }) {
  const map = useMap();

  useEffect(() => {
    if (focus === "route") return;
    if (focus === "me" && me) {
      map.flyTo([me.lat, me.lon], 16, { duration: 0.45 });
      return;
    }
    if (focus === "parking" && parking) {
      map.flyTo([parking.lat, parking.lon], 16, { duration: 0.45 });
      return;
    }
    map.flyTo(STIP, 14, { duration: 0.45 });
  }, [focus, parking?.id, me?.lat, me?.lon, map]);

  return null;
}

export default function App() {
  const [parkings, setParkings] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [nearest, setNearest] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [locating, setLocating] = useState(false);
  const [me, setMe] = useState(null);
  const [focus, setFocus] = useState("city");
  const [route, setRoute] = useState(null);
  const [trip, setTrip] = useState("");
  const [routing, setRouting] = useState(false);
  const [now, setNow] = useState(Date.now());

  function choose(id) {
    setSelectedId(id);
    setFocus("parking");
    setRoute(null);
    setTrip("");
  }

  function readLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("no-geo"));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => reject(new Error("denied")),
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  function locate() {
    setLocating(true);
    readLocation()
      .then((point) => {
        setMe(point);
        setFocus("me");
        setNotice("");
      })
      .catch(() => setNotice("Локацијата не е дозволена."))
      .finally(() => setLocating(false));
  }

  async function showRoute() {
    if (!destination) return;
    setRouting(true);
    setNotice("");
    try {
      const from = me ?? await readLocation();
      if (!me) setMe(from);
      const url = `https://router.project-osrm.org/route/v1/driving/${from.lon},${from.lat};${destination.lon},${destination.lat}?overview=full&geometries=geojson`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("route");
      const data = await res.json();
      const line = data.routes?.[0]?.geometry?.coordinates?.map(([lon, lat]) => [lat, lon]);
      if (!line?.length) throw new Error("route");
      const minutes = Math.max(1, Math.round(data.routes[0].duration / 60));
      const meters = data.routes[0].distance;
      const distance = meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;
      setRoute(line);
      setTrip(`${minutes} мин · ${distance}`);
      setFocus("route");
    } catch (err) {
      setRoute(null);
      setTrip("");
      setNotice(err.message === "denied" || err.message === "no-geo"
        ? "Локацијата не е дозволена."
        : "Патот не може да се најде.");
    } finally {
      setRouting(false);
    }
  }

  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    let stop = false;

    async function load() {
      try {
        const res = await fetch("/api/parkings");
        if (!res.ok) throw new Error("bad");
        const data = await res.json();
        if (!stop) {
          setParkings(data);
          setError("");
        }
      } catch {
        if (!stop) setError("Нема врска со серверот.");
      }
    }

    load();
    const timer = setInterval(load, 5000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, []);

  const selected = parkings.find((p) => p.id === selectedId) ?? null;

  useEffect(() => {
    if (!selected || selected.free_spots !== 0) {
      setNearest(null);
      return;
    }

    let stop = false;
    fetch(`/api/parkings/${selected.id}/nearest-free?limit=1`)
      .then((res) => res.json())
      .then((data) => {
        if (!stop) setNearest(data[0] ?? null);
      })
      .catch(() => {
        if (!stop) setNearest(null);
      });

    return () => {
      stop = true;
    };
  }, [selected?.id, selected?.free_spots]);

  const destination =
    selected && selected.free_spots > 0 ? selected : nearest?.parking ?? null;

  return (
    <div className="app">
      <div className="map-wrap">
        <div className="topbar">
          <div className="brand">
            <h1>Mestence</h1>
            <p>Паркинг во Штип</p>
          </div>
          <button
            type="button"
            className="locate"
            onClick={locate}
            disabled={locating}
            aria-label="Моја локација"
          >
            {locating ? "…" : (
              <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="3.2" fill="none" stroke="currentColor" strokeWidth="2" />
                <path d="M12 2.5v3.2M12 18.3v3.2M2.5 12h3.2M18.3 12h3.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>

        <MapContainer
          center={STIP}
          zoom={14}
          zoomControl={false}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap"
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapFocus focus={focus} parking={selected} me={me} />
          <RouteLine route={route} />
          {me && <Marker position={[me.lat, me.lon]} icon={meIcon} />}
          {parkings.map((parking) => (
            <Marker
              key={parking.id}
              position={[parking.lat, parking.lon]}
              icon={pinIcon(kindOf(parking), parking.id === selectedId)}
              eventHandlers={{ click: () => choose(parking.id) }}
            />
          ))}
        </MapContainer>

      </div>

      <section className="sheet">
        {error && <p className="error">{error}</p>}
        {notice && <p className="error">{notice}</p>}

        {!selected && (
          <div className="list">
            <p className="sheet-label">Паркинзи</p>
            {parkings.map((parking) => (
              <button
                key={parking.id}
                type="button"
                className={`lot lot-${kindOf(parking)}`}
                onClick={() => choose(parking.id)}
              >
                <span className="lot-mark" />
                <strong>{parking.name.replace("Паркинг ", "")}</strong>
                <em className={kindOf(parking)}>{statusText(parking)}</em>
              </button>
            ))}
          </div>
        )}

        {selected && (
          <div className="detail">
            <button type="button" className="back" onClick={() => { setSelectedId(null); setFocus("city"); setRoute(null); setTrip(""); }}>
              Сите паркинзи
            </button>
            <p className="name">{selected.name}</p>
            {selected.free_spots > 0 ? (
              <p className="count">{selected.free_spots}</p>
            ) : (
              <p className={`status ${kindOf(selected)}`}>{statusText(selected)}</p>
            )}

            {selected.free_spots > 0 && (
              <p className="meta">
                слободни од {selected.total_spots} · {ago(selected.checked_at, now)}
              </p>
            )}

            {selected.free_spots == null && (
              <p className="meta">Нема слика за овој паркинг.</p>
            )}

            {selected.free_spots === 0 && nearest && (
              <p className="meta">
                Најблиску: {nearest.parking.name} · {nearest.distance_m} m · {nearest.parking.free_spots} слободни
              </p>
            )}

            {selected.free_spots === 0 && !nearest && (
              <p className="meta">Нема друг паркинг со слободно место.</p>
            )}

            {destination && (
              <button type="button" className="go" onClick={showRoute} disabled={routing}>
                {routing ? "Го барам патот…" : `Насоки до ${destination.name}`}
              </button>
            )}
            {trip && <p className="meta">{trip}</p>}
          </div>
        )}
      </section>
    </div>
  );
}
