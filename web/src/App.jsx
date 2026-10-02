import { useMemo, useState } from "react";
import { planTrip } from "./api";
import TripForm from "./components/TripForm";
import RouteMap from "./components/RouteMap";
import StopList from "./components/StopList";
import DailyLog from "./components/DailyLog";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [day, setDay] = useState("");

  const selectedLog = useMemo(() => {
    if (!result?.daily_logs?.length) return null;
    return result.daily_logs.find((log) => log.date === day) || result.daily_logs[0];
  }, [result, day]);

  async function handlePlan(payload) {
    setLoading(true);
    setError("");
    try {
      const data = await planTrip(payload);
      setResult(data);
      setDay(data.daily_logs[0]?.date || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <div className="logo">DL</div>
          <div>
            <h1>DriverLog</h1>
            <p>Interstate truck driver’s Hours of Service trip planner</p>
          </div>
        </div>
        <div className="hos-pills">
          <span>11-hour driving</span>
          <span>14-hour window</span>
          <span>30-min break</span>
          <span>70-hr / 8-day</span>
          <span>10-hr sleeper</span>
        </div>
      </header>
      <main className="layout">
        <div>
          <TripForm onPlan={handlePlan} loading={loading} />
          {error ? <div className="error">{error}</div> : null}
        </div>
        <div className="results">
          {result ? (
            <>
              <RouteMap geometry={result.route.geometry} stops={result.route.stops} />
              <div className="card">
                <div className="summary">
                  <div className="stat">
                    <b>{result.summary.total_miles}</b>
                    <span>Total miles</span>
                  </div>
                  <div className="stat">
                    <b>{result.summary.driving_hours}h</b>
                    <span>Driving</span>
                  </div>
                  <div className="stat">
                    <b>{result.summary.days}</b>
                    <span>Log sheets</span>
                  </div>
                  <div className="stat">
                    <b>{result.summary.cycle_remaining}h</b>
                    <span>Cycle remaining</span>
                  </div>
                </div>
                <div className="legend">
                  <span><i className="dot" style={{ background: "#1f7a4d" }} /> Current / pickup</span>
                  <span><i className="dot" style={{ background: "#9b1c1c" }} /> Dropoff</span>
                  <span><i className="dot" style={{ background: "#b45309" }} /> Fuel</span>
                  <span><i className="dot" style={{ background: "#6d28d9" }} /> Sleeper / restart</span>
                  <span><i className="dot" style={{ background: "#64748b" }} /> 30-min break</span>
                </div>
              </div>
              <StopList stops={result.route.stops} />
              {selectedLog && (
                <DailyLog
                  log={selectedLog}
                  logs={result.daily_logs}
                  selected={selectedLog.date}
                  onSelect={setDay}
                />
              )}
            </>
          ) : (
            <div className="card empty">
              <div>
                <h2>No trip yet</h2>
                <p>
                  Plan a route and this map will show rest, fuel, pickup, and dropoff.
                  Daily log sheets are drawn to match an FMCSA paper log.
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
