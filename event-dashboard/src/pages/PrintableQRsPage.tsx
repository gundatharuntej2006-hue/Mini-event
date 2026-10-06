import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Printer,
  ArrowLeft,
  QrCode,
  ShieldCheck,
  MapPin,
  Compass,
  ExternalLink,
  Globe,
  RefreshCw,
} from 'lucide-react';
import QRCode from 'qrcode';

interface LocationPrintConfig {
  locationNumber: number;
  label: string;
  theme: string;
  riddle: string;
  target: string;
}

const LOCATIONS_FOR_PRINT: LocationPrintConfig[] = [
  {
    locationNumber: 1,
    label: 'LOCATION 1 — CAMPUS BORDER GATE',
    theme: 'Original Location 1',
    riddle: 'Walk toward the place where every campus day eventually ends — the border where students step out and the city begins. Vehicles often wait nearby for their next journey.',
    target: 'Find the metal plate where: S = The Silicon State of India, A = 100/2, L = The abbreviation for Extended Play, N = (17×100)+35',
  },
  {
    locationNumber: 2,
    label: 'LOCATION 2 — ROASTED BEAN TRAIL',
    theme: 'Original Location 2',
    riddle: 'Follow the familiar trail where tired students wander between classes, guided by the aroma of roasted beans and the promise of caffeine.',
    target: 'Find the metal plate where: S = The Silicon State, A = √4, L1 = The 11th letter of the alphabet, L2 = The 11th letter of the alphabet, N = 80² + 26',
  },
  {
    locationNumber: 3,
    label: "LOCATION 3 — NEWTON'S DOMAIN",
    theme: 'Original Location 5',
    riddle: 'Where gravity, light, and electricity are not just observed but calculated. A place where falling apples inspire formulas, and waves travel through wires and lenses. Seek the domain where Newton’s curiosity would feel at home.',
    target: 'Newton’s Domain of physics and calculations',
  },
  {
    locationNumber: 4,
    label: 'LOCATION 4 — BAKERY OF LOGIC',
    theme: 'Original Location 6',
    riddle: 'Here, heat transforms dough and patience turns sugar into delight. Yeast quietly performs its own chemistry, while aromas replace equations. Follow the scent of freshly baked logic.',
    target: 'Follow the scent of freshly baked logic.',
  },
  {
    locationNumber: 5,
    label: 'LOCATION 5 — THE MORNING HUT',
    theme: 'Original Location 7',
    riddle: 'Before lectures awaken minds, this humble refuge awakens people. Water boils, beans surrender their strength, and tired students rediscover energy. Seek the rustic hut that powers the campus mornings.',
    target: 'The rustic hut powering campus mornings.',
  },
  {
    locationNumber: 6,
    label: 'LOCATION 6 — WORDS IN STONE',
    theme: 'Original Location 8',
    riddle: 'Some knowledge is written in books, but here it is carved to last far longer. Seek the words that cannot be moved, resting in stone near the dreamers who design skylines.',
    target: 'Words carved in stone near the designers of skylines.',
  },
  {
    locationNumber: 7,
    label: 'LOCATION 7 — BLOCK ARM & DIMENSION ROOM',
    theme: 'Original Location 9',
    riddle: 'Take the letters that appear immediately after A, R, and M in the alphabet. Think of the dimensions we inhabit, add a zero, and then repeat the same number of dimensions once more.',
    target: 'Block letters after A, R, M. Room dimensions + 0 + dimensions repeated.',
  },
  {
    locationNumber: 8,
    label: 'LOCATION 8 — DISCOVERY CHAMBER',
    theme: 'Original Location 10',
    riddle: 'Seek the place where experiments either explode with excitement or quietly bloom with discovery. The exact number of bones in the adult human body will guide you.',
    target: 'Discovery experiments. Room: Number of bones in adult human body (206).',
  },
];

export function PrintableQRsPage() {
  const [printLayout, setPrintLayout] = useState<'sheet' | 'placards'>('sheet');
  const [baseUrl, setBaseUrl] = useState<string>(() => {
    return window.location.origin;
  });
  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);

  useEffect(() => {
    LOCATIONS_FOR_PRINT.forEach((loc, index) => {
      const canvas = canvasRefs.current[index];
      if (canvas) {
        const fullUrl = `${baseUrl.replace(/\/$/, '')}/round1/scan?location=${loc.locationNumber}`;
        QRCode.toCanvas(canvas, fullUrl, {
          width: 240,
          margin: 2,
          color: {
            dark: '#000000',
            light: '#ffffff',
          },
          errorCorrectionLevel: 'M',
        }).catch((err) => console.error(`Error rendering QR for Location ${loc.locationNumber}:`, err));
      }
    });
  }, [baseUrl]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans print:bg-white print:text-black">
      {/* Screen-Only Control Toolbar */}
      <div className="print:hidden sticky top-0 z-50 bg-[#061224]/95 backdrop-blur-md border-b border-cyan-500/30 px-4 py-3 sm:px-8">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              to="/round-1"
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors flex items-center gap-1.5 text-xs font-mono"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Round 1</span>
            </Link>

            <div>
              <h1 className="text-base font-bold text-white font-display flex items-center gap-2">
                <QrCode className="w-5 h-5 text-cyan-400" />
                <span>Physical Checkpoint QR Sheets (8 Locations)</span>
              </h1>
              <p className="text-[11px] text-cyan-400 font-mono">
                Official ODDyssey Protocol · 8 Stations · Reused across R1.1, R1.2, R1.3
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Base URL configuration */}
            <div className="flex items-center gap-2 bg-[#030712] border border-cyan-500/40 rounded-xl px-3 py-1.5 text-xs font-mono">
              <Globe className="w-4 h-4 text-cyan-400 shrink-0" />
              <label htmlFor="baseUrlInput" className="text-slate-400 shrink-0">Base URL:</label>
              <input
                id="baseUrlInput"
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://your-domain.com"
                className="bg-slate-800 text-cyan-300 border border-slate-700 rounded px-2 py-0.5 text-xs w-48 sm:w-64 focus:outline-none focus:border-cyan-400"
              />
              <button
                type="button"
                onClick={() => setBaseUrl(window.location.origin)}
                title="Reset to current origin"
                className="text-slate-400 hover:text-cyan-300 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center bg-[#030712] border border-cyan-500/30 rounded-xl p-1 text-xs font-mono">
              <button
                type="button"
                onClick={() => setPrintLayout('sheet')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  printLayout === 'sheet'
                    ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Grid Sheet (Compact)
              </button>
              <button
                type="button"
                onClick={() => setPrintLayout('placards')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  printLayout === 'placards'
                    ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Placards (1 / Page)
              </button>
            </div>

            <button
              type="button"
              onClick={handlePrint}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-mono font-bold text-xs tracking-wide shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all flex items-center gap-2"
            >
              <Printer className="w-4 h-4" />
              <span>Print / Save as PDF</span>
            </button>
          </div>
        </div>
      </div>

      {/* Screen Instructions Banner */}
      <div className="print:hidden max-w-6xl mx-auto px-4 pt-6 pb-2">
        <div className="p-4 rounded-2xl bg-cyan-950/30 border border-cyan-500/30 text-xs font-mono text-cyan-200 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Physical Checkpoint Deployment Guidelines</span>
            </div>
            <p className="text-slate-300">
              Print and laminate these 8 location QR badges. Mount each QR at its corresponding physical campus station.
              When participants scan, their browser opens <code className="text-cyan-300">/round1/scan?location=X</code>.
              The system validates whether that station is the squad&apos;s current assigned checkpoint target.
            </p>
          </div>
        </div>
      </div>

      {/* Printable Area */}
      <main className="max-w-6xl mx-auto p-4 sm:p-6 print:p-0 print:max-w-none">
        <div
          className={
            printLayout === 'sheet'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 print:grid print:grid-cols-2 print:gap-4'
              : 'space-y-8 print:space-y-0'
          }
        >
          {LOCATIONS_FOR_PRINT.map((loc, index) => {
            const locUrl = `${baseUrl.replace(/\/$/, '')}/round1/scan?location=${loc.locationNumber}`;
            return (
              <div
                key={loc.locationNumber}
                className={`bg-white text-slate-900 rounded-2xl p-5 border-2 border-slate-300 shadow-xl flex flex-col justify-between print:border-2 print:border-black print:rounded-xl print:p-4 print:shadow-none ${
                  printLayout === 'placards'
                    ? 'print:break-after-page print:min-h-screen print:flex print:flex-col print:justify-between'
                    : ''
                }`}
              >
                {/* Header */}
                <div className="text-center space-y-1.5 border-b-2 border-slate-200 pb-3 print:pb-2">
                  <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-100 text-slate-800 uppercase tracking-widest border border-slate-300">
                    <Compass className="w-3 h-3 text-cyan-600" />
                    <span>ODDYSSEY PROTOCOL</span>
                  </div>

                  <div className="font-mono text-xs font-black uppercase tracking-wider text-cyan-700">
                    Location Station 0{loc.locationNumber} of 08
                  </div>

                  <h2 className="text-lg font-black font-display text-slate-900 tracking-tight uppercase leading-tight">
                    {loc.label}
                  </h2>

                  <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-cyan-50 border border-cyan-200 text-[11px] font-mono font-bold text-cyan-900">
                    <MapPin className="w-3 h-3 text-cyan-600 shrink-0" />
                    <span className="truncate">{loc.target}</span>
                  </div>
                </div>

                {/* QR Code Presentation Box */}
                <div className="py-4 flex flex-col items-center justify-center space-y-2">
                  <div className="p-2.5 bg-white border-4 border-slate-900 rounded-xl shadow-md print:border-3 print:border-black flex items-center justify-center">
                    <canvas
                      ref={(el) => {
                        canvasRefs.current[index] = el;
                      }}
                      className="w-[200px] h-[200px] sm:w-[220px] sm:h-[220px] block"
                    />
                  </div>

                  <div className="text-center space-y-0.5">
                    <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider block">
                      Direct Checkpoint URL:
                    </span>
                    <a
                      href={locUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-[11px] font-bold text-blue-700 hover:underline break-all inline-flex items-center gap-1 print:text-black"
                    >
                      <span>{locUrl}</span>
                      <ExternalLink className="w-3 h-3 print:hidden shrink-0" />
                    </a>
                  </div>
                </div>

                {/* Riddle / Description */}
                <div className="space-y-2 border-t-2 border-slate-200 pt-3 print:pt-2">
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] font-mono text-slate-700 leading-snug">
                    <strong className="block text-slate-900 uppercase mb-0.5">Physical Clue:</strong>
                    {loc.riddle}
                  </div>
                </div>

                {/* Card Footer */}
                <div className="pt-2 text-center text-[9px] font-mono text-slate-400 print:text-slate-600 uppercase border-t border-slate-100 mt-2">
                  EVENT HQ · ODDyssey Protocol · Scan with Phone Camera
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
