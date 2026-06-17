"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8037";

interface Rates {
  wall_stud_labor: number;
  plywood_subfloor_labor: number;
  plywood_sheathing_labor: number;
  tji_joist_labor: number;
  concrete_labor: number;
  excavation_labor: number;
  hardware_install: number;
  concrete_pump_per_cy: number;
  crane_per_sqft: number;
  scaffold_per_sqft: number;
}

const DEFAULTS: Rates = {
  wall_stud_labor: 0,
  plywood_subfloor_labor: 0,
  plywood_sheathing_labor: 0,
  tji_joist_labor: 0,
  concrete_labor: 0,
  excavation_labor: 0,
  hardware_install: 0,
  concrete_pump_per_cy: 0,
  crane_per_sqft: 0,
  scaffold_per_sqft: 0,
};

const LABOR_FIELDS: { key: keyof Rates; label: string; unit: string; hint: string }[] = [
  { key: "wall_stud_labor",        label: "Wall Studs",              unit: "$ / piece", hint: "Labor to frame one stud" },
  { key: "plywood_subfloor_labor", label: "Subfloor Plywood",        unit: "$ / sheet", hint: "Labor to install one 4×8 sheet" },
  { key: "plywood_sheathing_labor",label: "Wall Sheathing",          unit: "$ / sheet", hint: "Labor to install one 4×8 sheet" },
  { key: "tji_joist_labor",        label: "TJI / I-Joists",          unit: "$ / piece", hint: "Labor per engineered joist" },
  { key: "concrete_labor",         label: "Concrete (pour + finish)", unit: "$ / CY",   hint: "Total labor per cubic yard" },
  { key: "excavation_labor",       label: "Excavation",              unit: "$ / LF",    hint: "Per linear foot of footing trench" },
  { key: "hardware_install",       label: "Hardware Install",         unit: "$ / piece", hint: "Per Simpson connector installed (optional)" },
];

const EQUIPMENT_FIELDS: { key: keyof Rates; label: string; unit: string; hint: string }[] = [
  { key: "concrete_pump_per_cy", label: "Concrete Pump",       unit: "$ / CY",    hint: "Pump rental cost per CY poured — multiplied by extracted concrete volume" },
  { key: "crane_per_sqft",       label: "Crane / Lift",        unit: "$ / sqft",  hint: "Equipment cost per sqft of floor area — proxy for project size" },
  { key: "scaffold_per_sqft",    label: "Scaffolding",         unit: "$ / sqft",  hint: "Per sqft of exterior wall area — estimated from sheathing quantities" },
];

function RateRow({ fieldKey, label, unit, hint, value, onChange }: {
  fieldKey: string; label: string; unit: string; hint: string;
  value: number; onChange: (v: number) => void;
}) {
  return (
    <div className="bg-[#222] rounded-lg p-4 flex items-center gap-4">
      <div className="flex-1">
        <label htmlFor={fieldKey} className="text-white font-medium text-sm">{label}</label>
        <p className="text-gray-500 text-xs mt-0.5">{hint}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-400 text-sm">$</span>
        <input
          id={fieldKey}
          type="number"
          min="0"
          step="0.01"
          value={value || ""}
          onChange={e => onChange(parseFloat(e.target.value) || 0)}
          className="w-24 bg-[#333] text-white text-sm rounded px-3 py-2 border border-[#444] focus:border-[#F5C518] outline-none text-right"
          placeholder="0.00"
        />
        <span className="text-gray-400 text-xs w-16">{unit.split("/ ")[1]}</span>
      </div>
    </div>
  )
}

export default function RatesPage() {
  const router = useRouter();
  const [rates, setRates] = useState<Rates>(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) { router.push("/login"); return; }
    fetch(`${API}/api/rates`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => {
        if (data && typeof data === "object" && !data.detail) {
          setRates({ ...DEFAULTS, ...data });
        }
      })
      .catch(() => {});
  }, [router]);

  async function handleSave() {
    setSaving(true); setError(""); setSaved(false);
    const token = getToken();
    try {
      const res = await fetch(`${API}/api/rates`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(rates),
      });
      if (!res.ok) throw new Error("Save failed");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Failed to save rates. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#1A1A1A] text-white">
      <nav className="bg-black px-6 py-4 flex items-center justify-between border-b border-[#F5C518]">
        <span className="text-[#F5C518] font-bold text-lg">Mel&apos;s Builders Pro Systems</span>
        <div className="flex gap-4 text-sm">
          <button onClick={() => router.push("/dashboard")} className="text-gray-400 hover:text-white">
            Dashboard
          </button>
          <span className="text-[#F5C518]">Rate Sheet</span>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-[#F5C518] mb-2">Labor Rate Sheet</h1>
        <p className="text-gray-400 text-sm mb-8">
          Enter your actual labor rates. These are multiplied against extracted quantities
          to generate a preliminary cost estimate in every PDF report. Leave fields at 0 to exclude them.
        </p>

        {/* Labor rates */}
        <h2 className="text-white font-semibold text-sm uppercase tracking-wider mt-2">Labor</h2>
        <div className="space-y-3">
          {LABOR_FIELDS.map(({ key, label, unit, hint }) => (
            <RateRow key={key} fieldKey={key} label={label} unit={unit} hint={hint}
              value={rates[key]} onChange={v => setRates(prev => ({ ...prev, [key]: v }))} />
          ))}
        </div>

        {/* Equipment rates */}
        <h2 className="text-white font-semibold text-sm uppercase tracking-wider mt-6">Equipment</h2>
        <p className="text-gray-500 text-xs -mt-1 mb-1">
          Quantities are derived automatically from extracted data — you only set the rate.
        </p>
        <div className="space-y-3">
          {EQUIPMENT_FIELDS.map(({ key, label, unit, hint }) => (
            <RateRow key={key} fieldKey={key} label={label} unit={unit} hint={hint}
              value={rates[key]} onChange={v => setRates(prev => ({ ...prev, [key]: v }))} />
          ))}
        </div>

        {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

        <div className="mt-8 flex items-center gap-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-[#F5C518] text-black font-bold px-8 py-3 rounded hover:bg-yellow-400 disabled:opacity-50 transition"
          >
            {saving ? "Saving…" : "Save Rates"}
          </button>
          {saved && <span className="text-green-400 text-sm">Saved — next PDF download will include cost estimate.</span>}
        </div>

        <p className="mt-6 text-gray-600 text-xs">
          Rates are stored per account. Saving new rates clears cached PDFs so all reports regenerate with updated costs.
        </p>
      </div>
    </div>
  );
}
