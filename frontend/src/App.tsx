import { useState, useEffect, useRef } from 'react';
// @ts-ignore
import { TestDatabase, TestAPI, SaveConfig, StartSync, GetConfig } from "../wailsjs/go/main/App";
// @ts-ignore
import { EventsOn } from "../wailsjs/runtime/runtime";

export default function App() {
  const [step, setStep] = useState(1);
  const [apiKey, setApiKey] = useState('');
  const [apiUrl, setApiUrl] = useState('https://api.peoplein.com');
  const [mdbPath, setMdbPath] = useState('C:\\Program Files (x86)\\eSSL\\eTimeTrackLite\\eTimeTrackLite1.mdb');
  const [machineName, setMachineName] = useState('Relay-1');
  
  const [apiTesting, setApiTesting] = useState(false);
  const [apiSuccess, setApiSuccess] = useState<boolean | null>(null);

  const [dbTesting, setDbTesting] = useState(false);
  const [dbSuccess, setDbSuccess] = useState<any>(null);

  const [isSyncing, setIsSyncing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    GetConfig().then((cfg: any) => {
      if (cfg && cfg.apiKey) {
        setApiKey(cfg.apiKey);
        setApiUrl(cfg.apiUrl);
        setMdbPath(cfg.mdbPath);
        setMachineName(cfg.machineName);
        setStep(5);
      }
    }).catch(() => {});

    // Listen for real-time logs from Go
    EventsOn("log-update", (msg: string) => {
      setLogs(prev => {
        const newLogs = [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`];
        if (newLogs.length > 100) return newLogs.slice(newLogs.length - 100);
        return newLogs;
      });
    });

    EventsOn("sync-update", (data: any) => {
      if (data.error) {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ERROR: ${data.error}`]);
      }
    });
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleTestApi = async () => {
    setApiTesting(true);
    try {
      await TestAPI(apiUrl, apiKey, machineName);
      setApiSuccess(true);
    } catch (err) {
      setApiSuccess(false);
    }
    setApiTesting(false);
  };

  const handleTestDb = async () => {
    setDbTesting(true);
    try {
      const result = await TestDatabase(mdbPath);
      setDbSuccess(result);
    } catch (err) {
      setDbSuccess(false);
    }
    setDbTesting(false);
  };

  const handleStartSync = async () => {
    try {
      await SaveConfig({ apiKey, apiUrl, mdbPath, machineName, syncIntervalMinutes: 5 });
      await StartSync();
      setIsSyncing(true);
      setStep(5);
    } catch (err) {
      console.error(err);
    }
  };

  // FLAT UI STYLING CONSTANTS
  const inputClass = "w-full px-4 py-3 bg-white border-2 border-slate-900 focus:outline-none focus:ring-0 transition-colors font-mono text-sm";
  const btnClass = "bg-slate-900 hover:bg-slate-800 text-white font-bold py-3 px-8 border-2 border-slate-900 transition-colors uppercase tracking-widest text-sm";
  const btnOutlineClass = "bg-white hover:bg-slate-50 text-slate-900 font-bold py-3 px-8 border-2 border-slate-900 transition-colors uppercase tracking-widest text-sm";

  return (
    <div className="min-h-screen bg-white flex flex-col font-sans text-slate-900">
      <header className="bg-white border-b-2 border-slate-900 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center">
          <div className="h-8 w-8 bg-slate-900 flex items-center justify-center text-white font-black mr-3">
            P
          </div>
          <h1 className="text-xl font-black tracking-tight uppercase">PeopleIN Relay</h1>
        </div>
        {step === 5 && (
          <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-900 border-2 border-green-900 text-xs font-bold uppercase">
            <div className="w-2 h-2 bg-green-500 animate-pulse"></div>
            Online
          </div>
        )}
      </header>

      <main className="flex-1 flex flex-col p-8 max-w-4xl w-full mx-auto">
        {step < 5 && (
          <div className="flex border-2 border-slate-900 mb-8 h-2">
            {[1,2,3,4].map((s) => (
              <div key={s} className={`flex-1 ${step >= s ? 'bg-slate-900' : 'bg-white'} ${s < 4 ? 'border-r-2 border-slate-900' : ''}`} />
            ))}
          </div>
        )}

        <div className="flex-1 border-2 border-slate-900 p-8 bg-white flex flex-col relative">
          {/* Background grid pattern for brutalist feel */}
          <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>

          <div className="relative z-10 flex-1 flex flex-col">
            {step === 1 && (
              <div className="text-center py-12 m-auto">
                <h2 className="text-4xl font-black uppercase tracking-tight mb-4">Connect eTimeTrackLite</h2>
                <p className="text-slate-600 mb-10 max-w-md mx-auto text-lg">
                  Automate attendance synchronization securely from your local network directly to PeopleIN. No more manual exports.
                </p>
                <button onClick={() => setStep(2)} className={btnClass}>
                  Initialize Setup
                </button>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6 m-auto w-full max-w-md">
                <div>
                  <h2 className="text-2xl font-black uppercase mb-1">API Credentials</h2>
                  <p className="text-slate-600">Enter your PeopleIN API authorization.</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold uppercase tracking-wider mb-2">API Key</label>
                    <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} className={inputClass} placeholder="sk_live_..." />
                  </div>
                  <div>
                    <label className="block text-sm font-bold uppercase tracking-wider mb-2">API URL</label>
                    <input type="text" value={apiUrl} onChange={e => setApiUrl(e.target.value)} className={inputClass} />
                  </div>
                </div>

                <div className="pt-4 flex items-center justify-between border-t-2 border-slate-900 pt-6 mt-6">
                  <button onClick={handleTestApi} disabled={apiTesting || !apiKey} className="font-bold uppercase text-sm hover:underline disabled:opacity-50">
                    {apiTesting ? 'Testing...' : 'Test Connection'}
                  </button>
                  
                  <div className="flex items-center gap-4">
                    {apiSuccess === true && <span className="text-green-600 font-bold uppercase text-sm">✓ Connected</span>}
                    {apiSuccess === false && <span className="text-red-600 font-bold uppercase text-sm">✕ Failed</span>}
                    <button onClick={() => setStep(3)} disabled={!apiSuccess} className={`${btnClass} disabled:opacity-50 disabled:cursor-not-allowed`}>
                      Next
                    </button>
                  </div>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6 m-auto w-full max-w-md">
                <div>
                  <h2 className="text-2xl font-black uppercase mb-1">Select Database</h2>
                  <p className="text-slate-600">Point the relay to your eTimeTrackLite MDB file.</p>
                </div>

                <div>
                  <label className="block text-sm font-bold uppercase tracking-wider mb-2">MDB File Path</label>
                  <input type="text" value={mdbPath} onChange={e => setMdbPath(e.target.value)} className={inputClass} />
                </div>

                <div className="pt-4 flex items-center justify-between border-t-2 border-slate-900 pt-6 mt-6">
                  <button onClick={handleTestDb} disabled={dbTesting || !mdbPath} className="font-bold uppercase text-sm hover:underline disabled:opacity-50">
                    {dbTesting ? 'Testing...' : 'Test Database'}
                  </button>

                  <button onClick={() => setStep(4)} disabled={!dbSuccess} className={`${btnClass} disabled:opacity-50 disabled:cursor-not-allowed`}>
                    Confirm
                  </button>
                </div>

                {dbSuccess && dbSuccess.success && (
                  <div className="mt-6 p-4 border-2 border-slate-900 bg-slate-50">
                    <h4 className="font-black uppercase mb-4 text-sm border-b-2 border-slate-200 pb-2">Database Stats</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="block text-xs font-bold uppercase text-slate-500 mb-1">Employees</span>
                        <span className="font-mono text-xl">{dbSuccess.employeeCount}</span>
                      </div>
                      <div>
                        <span className="block text-xs font-bold uppercase text-slate-500 mb-1">Records</span>
                        <span className="font-mono text-xl">{dbSuccess.attendanceCount}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {step === 4 && (
              <div className="text-center py-12 m-auto">
                <h2 className="text-4xl font-black uppercase tracking-tight mb-4">Ready for Sync</h2>
                <p className="text-slate-600 mb-10 max-w-md mx-auto text-lg">
                  The relay is configured and will synchronize attendance records automatically every 5 minutes in chunks of 500.
                </p>
                <button onClick={handleStartSync} className={btnClass}>
                  Start Synchronization
                </button>
              </div>
            )}

            {step === 5 && (
              <div className="flex flex-col h-full space-y-6">
                <div className="grid grid-cols-3 gap-6">
                  <div className="border-2 border-slate-900 p-4">
                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-1">Target Database</h3>
                    <p className="font-mono text-sm truncate" title={mdbPath}>eTimeTrackLite1.mdb</p>
                  </div>
                  <div className="border-2 border-slate-900 p-4">
                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-1">Sync Interval</h3>
                    <p className="font-mono text-sm">5 Minutes</p>
                  </div>
                  <div className="border-2 border-slate-900 p-4 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase text-slate-500 mb-1">Status</h3>
                      <p className="font-mono text-sm">{isSyncing ? 'Running' : 'Idle'}</p>
                    </div>
                    <button onClick={() => StartSync()} className="bg-slate-100 hover:bg-slate-200 text-xs font-bold uppercase px-3 py-1 border-2 border-slate-900 transition-colors">
                      Force Sync
                    </button>
                  </div>
                </div>

                <div className="flex-1 flex flex-col border-2 border-slate-900 bg-slate-50 min-h-[300px]">
                  <div className="border-b-2 border-slate-900 px-4 py-2 bg-slate-900 text-white flex justify-between items-center">
                    <h3 className="text-xs font-bold uppercase tracking-wider">Terminal Output</h3>
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-slate-700"></div>
                      <div className="w-3 h-3 rounded-full bg-slate-700"></div>
                      <div className="w-3 h-3 rounded-full bg-slate-700"></div>
                    </div>
                  </div>
                  <div className="flex-1 p-4 overflow-y-auto font-mono text-xs leading-relaxed text-slate-700 bg-slate-50">
                    {logs.length === 0 ? (
                      <span className="opacity-50">Waiting for events...</span>
                    ) : (
                      logs.map((log, i) => (
                        <div key={i} className={`mb-1 ${log.includes('ERROR') ? 'text-red-600 font-bold bg-red-100 px-1 inline-block' : ''}`}>
                          {log}
                        </div>
                      ))
                    )}
                    <div ref={logsEndRef} />
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4 border-t-2 border-slate-900">
                  <span className="text-xs font-bold text-slate-500 uppercase">Version 1.0.0</span>
                  <button onClick={() => setStep(1)} className="text-xs font-bold hover:underline uppercase text-slate-500">
                    Reconfigure
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
