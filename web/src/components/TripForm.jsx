import { useEffect, useState } from "react";
import { suggestLocations } from "../api";

const SAMPLES = [
  {
    label: "Midwest haul",
    current_location: "Chicago, IL",
    pickup_location: "Indianapolis, IN",
    dropoff_location: "Kansas City, MO",
    current_cycle_used: 18,
  },
  {
    label: "Coast to coast",
    current_location: "Newark, NJ",
    pickup_location: "Philadelphia, PA",
    dropoff_location: "Los Angeles, CA",
    current_cycle_used: 8,
  },
];

function PlaceField({ id, label, value, onChange, placeholder }) {
  const [open, setOpen] = useState(false);
  const [hits, setHits] = useState([]);

  useEffect(() => {
    if (value.trim().length < 3) {
      setHits([]);
      return undefined;
    }
    const handle = setTimeout(async () => {
      const results = await suggestLocations(value);
      setHits(results);
      setOpen(results.length > 0);
    }, 350);
    return () => clearTimeout(handle);
  }, [value]);

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => hits.length && setOpen(true)}
        autoComplete="off"
      />
      {open && (
        <div className="suggest">
          {hits.map((hit) => (
            <button
              type="button"
              key={hit.label}
              onClick={() => {
                onChange(hit.label);
                setOpen(false);
              }}
            >
              {hit.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TripForm({ onPlan, loading }) {
  const [form, setForm] = useState(SAMPLES[0]);

  function update(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function submit(event) {
    event.preventDefault();
    onPlan({
      current_location: form.current_location,
      pickup_location: form.pickup_location,
      dropoff_location: form.dropoff_location,
      current_cycle_used: Number(form.current_cycle_used),
    });
  }

  return (
    <form className="card form-card" onSubmit={submit}>
      <h2>Plan a trip</h2>
      <p className="lede">
        Enter locations and hours already used this cycle. The planner applies
        the 70-hour / 8-day property-carrier rules.
      </p>
      <PlaceField
        id="current"
        label="Current location"
        value={form.current_location}
        onChange={(v) => update("current_location", v)}
        placeholder="City, State"
      />
      <PlaceField
        id="pickup"
        label="Pickup location"
        value={form.pickup_location}
        onChange={(v) => update("pickup_location", v)}
        placeholder="Shipper city"
      />
      <PlaceField
        id="dropoff"
        label="Dropoff location"
        value={form.dropoff_location}
        onChange={(v) => update("dropoff_location", v)}
        placeholder="Receiver city"
      />
      <label htmlFor="cycle">Current cycle used (hrs)</label>
      <div className="cycle-row">
        <input
          id="cycle"
          type="number"
          min="0"
          max="70"
          step="0.25"
          value={form.current_cycle_used}
          onChange={(e) => update("current_cycle_used", e.target.value)}
        />
        <span>/ 70</span>
      </div>
      <p className="cycle-hint">
        Pickup and dropoff are 1 hour on-duty each. Fuel every 1,000 miles.
      </p>
      <button className="primary" type="submit" disabled={loading}>
        {loading ? "Building route and logs…" : "Generate route & ELD logs"}
      </button>
      <div className="samples">
        {SAMPLES.map((sample) => (
          <button
            type="button"
            key={sample.label}
            onClick={() => setForm(sample)}
          >
            {sample.label}
          </button>
        ))}
      </div>
    </form>
  );
}
