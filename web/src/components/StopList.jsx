export default function StopList({ stops }) {
  return (
    <div className="card panel">
      <h2>Stops & rest</h2>
      <p className="lede">Fuel, 30-minute breaks, sleeper rest, pickup, and dropoff along the route.</p>
      <div className="stops">
        {stops.map((stop, index) => (
          <div className="stop" key={`${stop.type}-${index}`}>
            <div className="time">{stop.clock}</div>
            <div>
              <strong>{stop.title}</strong>
              <br />
              <small>{stop.location.split(",")[0]} {stop.remark ? `· ${stop.remark}` : ""}</small>
            </div>
            <span className={`badge ${stop.type}`}>{stop.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
