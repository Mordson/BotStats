"use client";

import { CUSTOM_RANGE_VALUE, DateRange, TIME_RANGES, presetRange } from "@/lib/format";

interface TimeRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function todayDateInput(): string {
  return new Date().toISOString().slice(0, 10);
}

function defaultCustomRange(): DateRange {
  const untilDate = todayDateInput();
  const sinceDate = new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  return { kind: "custom", sinceDate, untilDate };
}

export default function TimeRangePicker({ value, onChange }: TimeRangePickerProps) {
  const selectValue = value.kind === "preset" ? String(value.hours) : CUSTOM_RANGE_VALUE;

  function handlePresetChange(raw: string) {
    onChange(raw === CUSTOM_RANGE_VALUE ? defaultCustomRange() : presetRange(Number(raw)));
  }

  function handleCustomDateChange(field: "sinceDate" | "untilDate", raw: string) {
    if (value.kind !== "custom" || !raw) return;
    const next = { ...value, [field]: raw };
    if (next.sinceDate > next.untilDate) {
      if (field === "sinceDate") next.untilDate = next.sinceDate;
      else next.sinceDate = next.untilDate;
    }
    onChange(next);
  }

  return (
    <div className="time-range-picker">
      <div>
        <span className="field-label">Przedział czasowy</span>
        <select value={selectValue} onChange={(e) => handlePresetChange(e.target.value)}>
          {TIME_RANGES.map((r) => (
            <option key={r.hours} value={r.hours}>
              {r.label}
            </option>
          ))}
          <option value={CUSTOM_RANGE_VALUE}>Własny zakres</option>
        </select>
      </div>
      {value.kind === "custom" && (
        <div className="custom-range-fields">
          <div>
            <span className="field-label">Od</span>
            <input
              type="date"
              value={value.sinceDate}
              max={value.untilDate}
              onChange={(e) => handleCustomDateChange("sinceDate", e.target.value)}
            />
          </div>
          <div>
            <span className="field-label">Do</span>
            <input
              type="date"
              value={value.untilDate}
              min={value.sinceDate}
              max={todayDateInput()}
              onChange={(e) => handleCustomDateChange("untilDate", e.target.value)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
