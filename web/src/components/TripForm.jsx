import { useEffect, useRef, useState } from "react";
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
  {
    label: "Texas triangle",
    current_location: "Dallas, TX",
    pickup_location: "Houston, TX",
    dropoff_location: "San Antonio, TX",
    current_cycle_used: 22,
  },
  {
    label: "Southeast run",
    current_location: "Atlanta, GA",
    pickup_location: "Jacksonville, FL",
    dropoff_location: "Miami, FL",
    current_cycle_used: 12,
  },
  {
    label: "Pacific corridor",
    current_location: "Seattle, WA",
    pickup_location: "Portland, OR",
    dropoff_location: "Sacramento, CA",
    current_cycle_used: 6,
  },
  {
    label: "I-80 Midwest",
    current_location: "Omaha, NE",
    pickup_location: "Des Moines, IA",
    dropoff_location: "Chicago, IL",
    current_cycle_used: 28,
  },
  {
    label: "Mountain west",
    current_location: "Denver, CO",
    pickup_location: "Salt Lake City, UT",
    dropoff_location: "Boise, ID",
    current_cycle_used: 15,
  },
  {
    label: "Northeast short",
    current_location: "Boston, MA",
    pickup_location: "New York, NY",
    dropoff_location: "Baltimore, MD",
    current_cycle_used: 40,
  },
  {
    label: "Produce haul",
    current_location: "Phoenix, AZ",
    pickup_location: "Nogales, AZ",
    dropoff_location: "Chicago, IL",
    current_cycle_used: 4,
  },
];

function PlaceField({ id, label, value, onChange, placeholder }) {
  const [open, setOpen] = useState(false);
  const [hits, setHits] = useState([]);
  const requestId = useRef(0);

  useEffect(() => {
    if (!open || value.trim().length < 3) {
      setHits([]);
      return undefined;
    }
    const current = ++requestId.current;
    const handle = setTimeout(async () => {
      const results = await suggestLocations(value);
      if (current !== requestId.current) return;
      setHits(results);
    }, 300);
    return () => clearTimeout(handle);
  }, [open, value]);

  function close() {
    requestId.current += 1;
    setOpen(false);
  }

  function choose(next) {
    onChange(next);
    close();
  }

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        value={value}
        placeholder={placeholder}
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          if (value.trim().length >= 3) setOpen(true);
        }}
        onBlur={close}
        autoComplete="off"
      />
      {open && hits.length > 0 && (
        <div className="suggest" role="listbox">
          {hits.map((hit) => (
            <button
              type="button"
              role="option"
              key={hit.label}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(hit.label)}
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
      <p className="samples-label">Sample trips</p>
      <div className="samples">
        {SAMPLES.map((sample) => (
          <button
            type="button"
            key={sample.label}
            className={
              form.current_location === sample.current_location &&
              form.pickup_location === sample.pickup_location &&
              form.dropoff_location === sample.dropoff_location &&
              Number(form.current_cycle_used) === Number(sample.current_cycle_used)
                ? "active"
                : undefined
            }
            onClick={() => setForm(sample)}
          >
            {sample.label}
          </button>
        ))}
      </div>
    </form>
  );
}
