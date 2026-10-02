const ROWS = [
  { key: "off_duty", label: "1. Off Duty" },
  { key: "sleeper", label: "2. Sleeper Berth" },
  { key: "driving", label: "3. Driving" },
  { key: "on_duty", label: "4. On Duty (not driving)" },
];

const ROW_Y = { off_duty: 0, sleeper: 1, driving: 2, on_duty: 3 };

function hoursLabel(index) {
  if (index === 0 || index === 24) return "Mid night";
  if (index === 12) return "Noon";
  return String(index % 12 === 0 ? 12 : index % 12);
}

export default function DailyLog({ log, selected, onSelect, logs }) {
  const width = 980;
  const left = 168;
  const top = 118;
  const gridW = 720;
  const rowH = 34;
  const hourW = gridW / 24;

  const points = [];
  log.grid.forEach((seg) => {
    const y = top + ROW_Y[seg.status] * rowH + rowH / 2;
    const x1 = left + (seg.start_min / 60) * hourW;
    const x2 = left + (seg.end_min / 60) * hourW;
    if (!points.length) points.push(`${x1},${y}`);
    const prev = points[points.length - 1];
    const prevY = Number(prev.split(",")[1]);
    if (prevY !== y) points.push(`${x1},${y}`);
    points.push(`${x2},${y}`);
  });

  const date = new Date(`${log.date}T00:00:00`);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const year = date.getFullYear();

  return (
    <div className="card panel">
      <h2>Daily log sheets</h2>
      <p className="lede">
        FMCSA-style record of duty status. Longer trips produce one sheet per day.
      </p>
      <div className="log-nav">
        {logs.map((item, index) => (
          <button
            key={item.date}
            className={item.date === selected ? "active" : ""}
            onClick={() => onSelect(item.date)}
            type="button"
          >
            Day {index + 1} · {item.date}
          </button>
        ))}
      </div>
      <svg viewBox={`0 0 ${width} 620`} width="100%" role="img" aria-label="Drivers daily log">
        <rect x="12" y="12" width={width - 24} height="596" fill="#fffdf8" stroke="#1a2332" />
        <text x="28" y="42" fontFamily="Source Serif 4, Georgia, serif" fontSize="22" fontWeight="700">
          Drivers Daily Log
        </text>
        <text x="28" y="64" fontSize="11" fill="#5b6b7f">
          (24 hours)
        </text>
        <text x="250" y="42" fontSize="13">
          {month} / {day} / {year}
        </text>
        <text x="250" y="60" fontSize="10" fill="#5b6b7f">
          (month) (day) (year)
        </text>
        <text x="620" y="38" fontSize="10">
          Original — File at home terminal.
        </text>
        <text x="620" y="52" fontSize="10">
          Duplicate — Driver retains in his/her possession for 8 days.
        </text>
        <text x="28" y="92" fontSize="12">
          From: {log.from}
        </text>
        <text x="360" y="92" fontSize="12">
          To: {log.to}
        </text>
        <rect x="700" y="74" width="90" height="28" fill="none" stroke="#1a2332" />
        <text x="708" y="86" fontSize="9">
          Miles driving
        </text>
        <text x="708" y="98" fontSize="12" fontWeight="700">
          {log.total_miles}
        </text>
        <rect x="800" y="74" width="148" height="28" fill="none" stroke="#1a2332" />
        <text x="808" y="86" fontSize="9">
          Carrier / home terminal
        </text>
        <text x="808" y="98" fontSize="11">
          DriverLog Express
        </text>

        {ROWS.map((row, i) => (
          <g key={row.key}>
            <text x="24" y={top + i * rowH + 22} fontSize="11">
              {row.label}
            </text>
            <rect x={left} y={top + i * rowH} width={gridW} height={rowH} fill={i % 2 ? "#f7f1e6" : "#fff"} stroke="#1a2332" />
            {Array.from({ length: 24 }).map((_, hour) =>
              [0, 1, 2, 3].map((tick) => (
                <line
                  key={`${row.key}-${hour}-${tick}`}
                  x1={left + hour * hourW + (tick * hourW) / 4}
                  x2={left + hour * hourW + (tick * hourW) / 4}
                  y1={top + i * rowH}
                  y2={top + (i + 1) * rowH}
                  stroke={tick === 0 ? "#1a2332" : "#b9b09f"}
                  strokeWidth={tick === 0 ? 1 : 0.5}
                />
              ))
            )}
          </g>
        ))}
        {Array.from({ length: 25 }).map((_, hour) => (
          <text
            key={`h-${hour}`}
            x={left + hour * hourW}
            y={top - 8}
            fontSize="9"
            textAnchor="middle"
          >
            {hoursLabel(hour)}
          </text>
        ))}
        <rect x={left + gridW} y={top} width="58" height={rowH * 4} fill="#0b1f3a" />
        <text x={left + gridW + 8} y={top - 8} fontSize="9" fill="#0b1f3a">
          Total Hours
        </text>
        {ROWS.map((row, i) => (
          <text key={`t-${row.key}`} x={left + gridW + 10} y={top + i * rowH + 22} fontSize="12" fill="#fff">
            {log.totals[row.key].toFixed(2)}
          </text>
        ))}
        <polyline points={points.join(" ")} fill="none" stroke="#0b1f3a" strokeWidth="2.4" />

        <text x="28" y="280" fontSize="12" fontWeight="700">
          Remarks
        </text>
        <line x1="28" y1="286" x2="948" y2="286" stroke="#1a2332" />
        {log.remarks.slice(0, 8).map((remark, i) => (
          <text key={`${remark.time}-${i}`} x="28" y={306 + i * 16} fontSize="11">
            {remark.time} {remark.status}: {remark.text} — {remark.location.split(",")[0]}
          </text>
        ))}
        <text x="28" y="450" fontSize="11" fontWeight="700">
          Recap complete at end of day
        </text>
        <rect x="28" y="460" width="300" height="86" fill="none" stroke="#1a2332" />
        <text x="40" y="478" fontSize="12" fontWeight="700">
          70 Hour / 8 Day
        </text>
        <text x="40" y="498" fontSize="11">
          A. On duty last 7 days including today: {log.recap.a}
        </text>
        <text x="40" y="516" fontSize="11">
          B. Hours available tomorrow (70 − A): {log.recap.b}
        </text>
        <text x="40" y="534" fontSize="11">
          C. On duty last 5 days: {log.recap.c}
        </text>
        <text x="350" y="478" fontSize="11">
          Shipping documents / shipper & commodity
        </text>
        <text x="350" y="498" fontSize="11" fill="#5b6b7f">
          Enter name of place reported and where released from work,
        </text>
        <text x="350" y="514" fontSize="11" fill="#5b6b7f">
          and where each change of duty occurred. Home terminal time.
        </text>
        <text x="28" y="572" fontSize="10" fill="#5b6b7f">
          Property-carrying driver · no adverse driving conditions · fuel at least every 1,000 miles
        </text>
      </svg>
    </div>
  );
}
