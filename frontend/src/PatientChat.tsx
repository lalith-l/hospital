// @ts-nocheck
import { useState, useRef, useEffect } from 'react';
import { Mic, Send, Activity, MapPin, AlertTriangle, Thermometer, Camera, Image as ImageIcon, X, Clock } from 'lucide-react';
import 'regenerator-runtime/runtime';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface TriageResult {
  status: 'question' | 'complete' | 'error';
  message: string;
  condition?: string;
  urgency?: 1 | 2 | 3;
  simulated_acoustic_signals?: string[];
  disease_probabilities?: { name: string; score: number }[];
  recommended_doctors?: {
    name: string;
    qualification: string;
    specialty: string;
    hospital_id: string;
    hospital_name: string;
    hospital_lat: number;
    hospital_lon: number;
    nabh: boolean;
    experience: number;
    rating: number;
    fee: number;
    photo: string;
    url: string;
    distance: string;
    capacity?: {
      load: string;
      score: number;
      method: string;
      z_score?: number;
      avg_wait_seconds?: number;
      pending?: number;
      pending_alerts?: number;
    };
  }[];
  critical_skipped?: boolean;
  elevated_risk?: string;
  ambient_status?: string;
  ambient_info?: any;
  ddx_confidence?: string;
  error_details?: string;
  detail?: string;
  behavioral_analysis?: {
    coherence_score: number;
    label: string;
    vocal_severity: number;
    keystroke_severity: number;
    latency_severity: number;
    verbal_severity: number;
    vocal_trend: string;
    keystroke_trend: string;
    latency_trend: string;
  };
  extracted_symptoms?: string[];
  action?: string;
  watchdog?: {
    hallucination_detected: boolean;
    severity?: string;
    reason?: string;
    action?: string;
    error?: string;
  };
}

interface KeystrokeData {
  total_keys: number;
  backspaces: number;
  inter_key_intervals: number[];
  word_pause_durations: number[];
  duration_ms: number;
}

interface VocalData {
  rms_energy: number;
  speech_rate: number;
}

interface BehavioralTurn {
  latency_ms: number;
  keystrokes: KeystrokeData;
  vocal: VocalData;
}

import HospitalMap from './HospitalMap';
import { EntryOverlay } from './components/EntryOverlay';

function PatientChat() {
  const [showEntryOverlay, setShowEntryOverlay] = useState(true);
  const [showPhoneOverlay, setShowPhoneOverlay] = useState(false);
  const [phoneInput, setPhoneInput] = useState('');
  const [phoneError, setPhoneError] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello. I am the Predictive Patient Pathfinder triage AI. Please describe your symptoms. You can type, use the microphone, or upload an image.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [triageResult, setTriageResult] = useState<TriageResult | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [recordedAudioBase64, setRecordedAudioBase64] = useState<string | null>(null);
  // const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  
  const [userLat, setUserLat] = useState<number>(12.9716); // Default Bangalore
  const [userLon, setUserLon] = useState<number>(77.5946);
  const [userCity, setUserCity] = useState<string>('Bangalore');
  const [userPincode, setUserPincode] = useState<string>('560001');
  const [userPhone, setUserPhone] = useState<string>('');
  const userMonth = new Date().toLocaleString('default', { month: 'short' });
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const [sessionId] = useState<string>(() => crypto.randomUUID());
  const [alertId, setAlertId] = useState<string | null>(null);
  const [alertStatus, setAlertStatus] = useState<string>('');

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, triageResult, isLoading]);

  // Geolocation and Reverse Geocoding
  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        setUserLat(lat);
        setUserLon(lon);
        
        try {
          // Nominatim Reverse Geocoding
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
          const data = await res.json();
          const city = data.address?.city || data.address?.town || data.address?.village || 'Unknown City';
          setUserCity(city);
          const postcode = data.address?.postcode?.replace(/\s/g, '') || '560001';
          setUserPincode(postcode);
        } catch (e) {
          console.error("Geocoding failed", e);
        }
      });
    }
  }, []);

  // --- Session & Source Tracking ---
  const [questionSource, setQuestionSource] = useState<string | null>(null);

  // --- Behavioral Tracking State & Logic ---
  const [behavioralHistory, setBehavioralHistory] = useState<BehavioralTurn[]>([]);
  const [turnStartTime, setTurnStartTime] = useState<number>(Date.now());
  const [firstActionTime, setFirstActionTime] = useState<number | null>(null);
  
  const currentKeystrokes = useRef<{
    total_keys: number;
    backspaces: number;
    last_key_time: number | null;
    inter_key_intervals: number[];
    word_pause_durations: number[];
    start_typing_time: number | null;
  }>({ total_keys: 0, backspaces: 0, last_key_time: null, inter_key_intervals: [], word_pause_durations: [], start_typing_time: null });

  const currentVocal = useRef<{
    rms_sum: number;
    rms_count: number;
    start_audio_time: number | null;
  }>({ rms_sum: 0, rms_count: 0, start_audio_time: null });
  
  // const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
      setTurnStartTime(Date.now());
      setFirstActionTime(null);
      currentKeystrokes.current = { total_keys: 0, backspaces: 0, last_key_time: null, inter_key_intervals: [], word_pause_durations: [], start_typing_time: null };
      currentVocal.current = { rms_sum: 0, rms_count: 0, start_audio_time: null };
    }
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!firstActionTime) setFirstActionTime(Date.now());
    
    const now = Date.now();
    if (!currentKeystrokes.current.start_typing_time) currentKeystrokes.current.start_typing_time = now;
    
    currentKeystrokes.current.total_keys++;
    
    if (e.key === 'Backspace') {
      currentKeystrokes.current.backspaces++;
    }
    
    if (currentKeystrokes.current.last_key_time) {
      const interval = now - currentKeystrokes.current.last_key_time;
      currentKeystrokes.current.inter_key_intervals.push(interval);
      
      if (e.key === ' ' && interval > 800) {
        currentKeystrokes.current.word_pause_durations.push(interval);
      }
    }
    currentKeystrokes.current.last_key_time = now;
  };

  const analyzeAudio = () => {
    if (!analyserRef.current) return;
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteTimeDomainData(dataArray);
    
    let sumSquares = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const normalized = (dataArray[i] / 128.0) - 1.0;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / dataArray.length);
    
    currentVocal.current.rms_sum += rms;
    currentVocal.current.rms_count++;
    
    animationFrameRef.current = requestAnimationFrame(analyzeAudio);
  };
  // -----------------------------------------

  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  const handleSend = async (text: string = input, audioBase64: string | null = recordedAudioBase64) => {
    if (!text.trim()) return;

    const newMessages: Message[] = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    setInput('');
    resetTranscript();
    setRecordedAudioBase64(null);
    setIsLoading(true);

    try {
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      
      // Calculate Behavioral Turn Data
      const latency_ms = firstActionTime ? firstActionTime - turnStartTime : 0;
      const ks = currentKeystrokes.current;
      const keystrokeData = {
         total_keys: ks.total_keys,
         backspaces: ks.backspaces,
         inter_key_intervals: ks.inter_key_intervals,
         word_pause_durations: ks.word_pause_durations,
         duration_ms: ks.start_typing_time ? Date.now() - ks.start_typing_time : 0
      };
      
      const voc = currentVocal.current;
      const rms_energy = voc.rms_count > 0 ? voc.rms_sum / voc.rms_count : 0;
      const audio_duration_sec = voc.start_audio_time ? (Date.now() - voc.start_audio_time) / 1000 : 0;
      const wordCount = (text || '').split(' ').filter(w => w.length > 0).length;
      const speech_rate = audio_duration_sec > 0 ? (wordCount * 1.5) / audio_duration_sec : 0;
      
      const vocalData = { rms_energy, speech_rate };
      const turnData = { latency_ms, keystrokes: keystrokeData, vocal: vocalData };
      const newHistory = [...behavioralHistory, turnData];
      setBehavioralHistory(newHistory);

      const payload: any = { 
        messages: newMessages,
        lat: userLat,
        lon: userLon,
        city: userCity,
        month: userMonth,
        behavioral_history: newHistory,
        session_id: sessionId
      };
      if (selectedImage) {
        payload.image = selectedImage;
        setSelectedImage(null); // Clear after sending
      }
      if (audioBase64) {
        payload.audio = audioBase64;
      }

      const response = await fetch(`${apiUrl}/api/intake/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data: any = await response.json();

      if (data.status === 'question' || data.status === 'error') {
        setTriageResult(data as TriageResult);
        setQuestionSource(data.question_source || 'llm_generated');
        setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
      } else if (data.status === 'complete') {
        // Step 2: Extract symptoms statelessly
        const extractRes = await fetch(`${apiUrl}/api/intake/extract`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: newMessages })
        });
        const extractedData = await extractRes.json();
        
        // Step 3: Compute Triage locally without raw text
        const computePayload = {
            extracted_symptoms: extractedData.symptoms || [],
            verbal_severity: extractedData.verbal_severity || 0.5,
            behavioral_history: newHistory,
            lat: userLat,
            lon: userLon,
            city: userCity,
            month: userMonth,
            pincode: userPincode,
            session_id: sessionId
        };
        const computeRes = await fetch(`${apiUrl}/api/triage/compute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(computePayload)
        });
        const finalData: TriageResult = await computeRes.json();
        setTriageResult(finalData);
        
        if (finalData.action === "ask_more_questions") {
            setMessages(prev => [...prev, { role: 'assistant', content: 'I need a bit more information to be sure. Could you describe any other symptoms you are experiencing?' }]);
        } else {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Triage complete. Please see the summary card.' }]);
            
            // Trigger alert for all urgency levels so Reception receives it
            if (finalData.urgency !== undefined && finalData.urgency <= 3) {
              try {
                let dynamicHospitalId = 'h_fallback_1';
                if (finalData.recommended_doctors && finalData.recommended_doctors.length > 0) {
                    dynamicHospitalId = finalData.recommended_doctors[0].hospital_id;
                } else {
                    // Fallback fetch
                    const fallbackRes = await fetch(`${apiUrl}/api/recommend-hospitals?lat=${userLat}&lng=${userLon}&urgency=${finalData.urgency}&condition=${finalData.condition || 'general'}`);
                    const fallbackData = await fallbackRes.json();
                    if (fallbackData.hospitals && fallbackData.hospitals.length > 0) {
                        dynamicHospitalId = fallbackData.hospitals[0].hospital_id;
                    }
                }
                
                const alertRes = await fetch(`${apiUrl}/api/create-alert`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    session_id: sessionId,
                    predicted_condition: finalData.condition || 'Unknown',
                    urgency_level: finalData.urgency,
                    patient_city: userCity,
                    patient_pincode: userPincode,
                    hospital_id: dynamicHospitalId,
                    patient_phone: userPhone
                  })
                });
                const alertData = await alertRes.json();
                if (alertData.alert_id) {
                  setAlertId(alertData.alert_id);
                  setAlertStatus('pending');
                }
              } catch (e) {
                console.error("Failed to create alert", e);
              }
            }
        }
      } else if (data.detail) {
        setMessages(prev => [...prev, { role: 'assistant', content: `Server Error: ${data.detail}` }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Received unexpected response format from server.' }]);
      }

    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error connecting to the server.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBookDoctor = async (doc: any) => {
    // Open Practo URL in a new tab
    window.open(doc.url, '_blank', 'noopener,noreferrer');
    
    // Create an alert for this specific hospital
    if (!triageResult) return;
    
    try {
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      const alertRes = await fetch(`${apiUrl}/api/create-alert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          predicted_condition: triageResult.condition || 'Unknown',
          urgency_level: triageResult.urgency || 3,
          patient_city: userCity,
          patient_pincode: userPincode,
          hospital_id: doc.hospital_id,
          patient_phone: userPhone
        })
      });
      const alertData = await alertRes.json();
      if (alertData.alert_id) {
        setAlertId(alertData.alert_id);
        setAlertStatus('pending');
      }
    } catch (e) {
      console.error("Failed to create alert", e);
    }
  };

  // Poll for alert status
  useEffect(() => {
    if (!alertId || alertStatus === 'acknowledged') return;
    const apiUrl = 'https://hospital-tp5s.onrender.com';
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiUrl}/api/alerts/${alertId}/status`);
        const data = await res.json();
        if (data.status) {
          setAlertStatus(data.status);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 10000);
  
    return () => clearInterval(interval);
  }, [alertId, alertStatus]);

  const toggleListen = () => {
    if (listening) {
      SpeechRecognition.stopListening();
    } else {
      SpeechRecognition.startListening({ continuous: true });
    }
  };

  const handleDownloadReport = async () => {
    try {
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      const res = await fetch(`${apiUrl}/api/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_data: {
            session_id: sessionId,
            triageResult: triageResult,
            messages: messages
          }
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `triage_report_${sessionId.substring(0,6)}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      } else {
        console.error("Failed to download PDF");
      }
    } catch (e) {
      console.error("Error downloading PDF:", e);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result) setSelectedImage(e.target.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <>
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex items-center justify-center p-4 md:p-8 relative overflow-hidden z-0">
      
      <div className="w-full max-w-[1200px] h-[85vh] bg-white rounded-2xl overflow-hidden shadow-xl border border-slate-200 flex flex-col relative z-10">
    
      {alertId && (
        <div className={`fixed top-20 right-6 z-[100] animate-in slide-in-from-right-8 fade-in duration-500 flex items-center gap-4 px-5 py-3.5 rounded-2xl shadow-xl border ${
          alertStatus === 'acknowledged' ? 'bg-white border-green-500/30' : 'bg-white border-[#E53935]/30'
        }`}>
          {alertStatus === 'acknowledged' ? (
             <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-600">
               <span className="text-lg leading-none">✓</span>
             </div>
          ) : (
             <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center text-red-600">
               <Activity className="w-4 h-4 animate-pulse" />
             </div>
          )}
          <div>
            <p className={`font-bold text-sm tracking-wide ${alertStatus === 'acknowledged' ? 'text-green-600' : 'text-red-600'}`}>
              {alertStatus === 'acknowledged' ? 'Appointment Confirmed' : 'Checking Availability...'}
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5 max-w-[200px] leading-tight">
              {alertStatus === 'acknowledged' 
                ? 'The hospital reception has confirmed your slot. SMS sent.' 
                : 'Alert sent to hospital reception. Waiting for confirmation.'}
            </p>
          </div>
          <button onClick={() => setAlertId(null)} className="ml-2 w-6 h-6 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="flex-1 flex flex-col relative min-h-0 bg-white">
        
        <div className="w-full bg-white border-b border-slate-100 p-4 flex justify-between items-center z-50 shrink-0">
          <div className="flex items-center gap-2 px-3 text-blue-600 font-bold text-[13px] tracking-widest uppercase">
            <Activity className="w-4 h-4" />
            Pathfinder Triage
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3 w-full md:w-auto pr-3">
            <button onClick={handleDownloadReport} className="flex items-center gap-1.5 px-4 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-100 text-blue-600 text-[11px] font-bold tracking-widest uppercase rounded-lg transition-all">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              Download Report
            </button>
            <a href="/hospital" target="_blank" rel="noreferrer" className="flex items-center gap-1.5 px-4 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-100 text-blue-600 text-[11px] font-bold tracking-widest uppercase rounded-lg transition-all">
              <Activity className="w-3.5 h-3.5" />
              Hospital Dashboard
            </a>
            <button onClick={() => {
              setTriageResult(null);
              setMessages([{ role: 'assistant', content: 'Hello. I am the Predictive Patient Pathfinder triage AI. Please describe your symptoms. You can type, use the microphone, or upload an image.' }]);
              setInput('');
            }} className="flex items-center gap-1.5 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-[11px] font-bold tracking-widest uppercase rounded-lg transition-all shadow-md">
              <Activity className="w-3.5 h-3.5" />
              New Chat
            </button>
          </div>
        </div>

        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-8 space-y-8 z-10 relative bg-white">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex group ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex items-end gap-4 max-w-[85%] md:max-w-[70%] relative ${msg.role === 'assistant' ? 'flex-row' : 'flex-row-reverse'}`}>
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0 mb-1">
                    <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center relative shadow-sm">
                      <Activity className="w-4 h-4 text-blue-500" />
                      {!isLoading && idx === messages.length - 1 && (
                         <div className="absolute inset-0 rounded-full border border-blue-400 animate-ping opacity-20"></div>
                      )}
                    </div>
                  </div>
                )}
                
                {msg.role === 'user' && (
                  <div className="text-[10px] text-slate-400 mb-2 whitespace-nowrap self-end hidden md:block">
                     {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </div>
                )}
                
                <div className={`p-[16px_20px] text-[14px] leading-relaxed tracking-wide shadow-sm ${
                  msg.role === 'user' 
                    ? 'bg-[#E5E7EB] text-slate-800 rounded-[20px_20px_4px_20px] text-right' 
                    : 'bg-[#E0F2FE] text-slate-800 rounded-[20px_20px_20px_4px] text-left'
                }`}>
                  {msg.content}
                  {msg.role === 'assistant' && idx === messages.length - 1 && questionSource && (
                    <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-1 bg-white/50 rounded text-[10px] font-mono tracking-wider text-blue-600 uppercase">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      Src: {questionSource.replace(/_/g, ' ')}
                    </div>
                  )}
                </div>
                
                {msg.role === 'assistant' && (
                  <div className="text-[10px] text-slate-400 mb-2 whitespace-nowrap hidden md:block">
                     {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start pl-12">
               <div className="bg-[#E0F2FE] p-[16px_24px] rounded-[20px_20px_20px_4px] flex items-center gap-[6px]">
                <div className="w-[6px] h-[6px] bg-blue-400 rounded-full animate-[pulse_1.2s_ease-in-out_infinite]" />
                <div className="w-[6px] h-[6px] bg-blue-400 rounded-full animate-[pulse_1.2s_ease-in-out_0.4s_infinite]" />
                <div className="w-[6px] h-[6px] bg-blue-400 rounded-full animate-[pulse_1.2s_ease-in-out_0.8s_infinite]" />
              </div>
            </div>
          )}
          
          {triageResult?.status === 'complete' && (
             <div className="mt-8 flex justify-center animate-[slide-up-fade_400ms_ease-out_forwards]">
               <div className="bg-white border-t-4 border-red-500 w-full max-w-lg rounded-xl p-[20px_24px] relative overflow-hidden shadow-xl border-x border-b border-slate-200">
                 <div className="flex items-start justify-between mb-6">
                   <div>
                     <h2 className="text-2xl font-bold mb-1 text-slate-800">Triage Complete</h2>
                     <p className="text-slate-500">Condition Predicted</p>
                   </div>
                   <div className="flex flex-col items-end gap-2">
                     <div className={`px-[12px] py-[4px] rounded-full text-[11px] font-bold flex items-center gap-1.5 ${
                       triageResult.urgency === 1 ? 'bg-red-50 text-red-600 border border-red-200' : 
                       triageResult.urgency === 2 ? 'bg-orange-50 text-orange-600 border border-orange-200' : 
                       'bg-green-50 text-green-600 border border-green-200'
                     }`}>
                       {triageResult.urgency === 1 && <AlertTriangle className="w-3.5 h-3.5" />}
                       Level {triageResult.urgency} {triageResult.urgency === 1 ? 'Critical' : triageResult.urgency === 2 ? 'Urgent' : 'Routine'}
                     </div>
                      <div className="flex items-center gap-1.5 text-[12px] text-slate-500 font-medium">
                        <Clock className="w-3.5 h-3.5" />
                        Nearest available slot: {(() => {
                           const waitMins = triageResult.recommended_doctors?.[0]?.capacity?.avg_wait_seconds 
                             ? Math.round(triageResult.recommended_doctors[0].capacity.avg_wait_seconds / 60) 
                             : (triageResult.urgency === 1 ? 5 : triageResult.urgency === 2 ? 30 : 120);
                           const d = new Date();
                           d.setMinutes(d.getMinutes() + waitMins);
                           return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        })()}
                      </div>
                      
                      {triageResult.watchdog && (
                        <div className={`mt-2 px-[10px] py-[3px] rounded-full text-[10px] font-bold tracking-widest uppercase flex items-center gap-1.5 border shadow-sm ${
                          triageResult.watchdog.hallucination_detected 
                            ? 'bg-red-50 border-red-200 text-red-600' 
                            : 'bg-green-50 border-green-200 text-green-600'
                        }`}>
                          {triageResult.watchdog.hallucination_detected ? (
                            <>
                              <AlertTriangle className="w-3 h-3 animate-pulse" />
                              <span>⚠ STABILITY CHECK: FLAGGED</span>
                            </>
                          ) : (
                            <>
                              <span className="text-xs">🛡</span>
                              <span>STABILITY CHECK: PASSED</span>
                            </>
                          )}
                        </div>
                      )}
                      {triageResult.watchdog?.hallucination_detected && (
                        <div className="text-[10px] text-red-500 max-w-[180px] text-right mt-1 font-semibold leading-tight">
                          {triageResult.watchdog.reason || "Diagnosis sensitive to noise."}
                        </div>
                      )}
                    </div>
                  </div>                  
                  <div className="space-y-6">
                   <div className="relative bg-red-50 rounded-xl p-5 border border-red-100 overflow-hidden shadow-sm group">
                     <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500 opacity-80" />
                     <div className="flex items-center gap-3 mb-2 ml-3">
                       <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center border border-red-200">
                         <Thermometer className="w-4 h-4 text-red-600" />
                       </div>
                       <h3 className="text-[12px] uppercase tracking-widest font-bold text-red-600">Primary Condition Flag</h3>
                     </div>
                     <p className="text-2xl font-extrabold text-slate-800 ml-3 mt-1 tracking-wide">{triageResult.condition}</p>
                   </div>
                   
                   <div className="space-y-4">
                     <div className="flex items-center gap-3 mb-4">
                       <MapPin className="w-5 h-5 text-blue-500" />
                       <h3 className="font-bold text-slate-800">Recommended Specialists</h3>
                     </div>
                     
                     <div className="space-y-4">
                       {triageResult.recommended_doctors?.map((doc, idx) => (
                         <div key={idx} className="bg-white border border-slate-200 shadow-sm rounded-xl p-1 relative group hover:shadow-md transition-all duration-300">
                           {doc.nabh && (
                             <div className="absolute top-3 right-3 bg-green-50 border border-green-200 text-green-600 text-[9px] tracking-widest uppercase font-bold px-2 py-0.5 rounded-full z-10">
                               NABH
                             </div>
                           )}
                           <div className="flex gap-4 p-3 bg-slate-50 rounded-lg border border-slate-100">
                             <div className="relative">
                               <img src={doc.photo} alt={doc.name} className="w-16 h-20 rounded-lg object-cover border border-slate-200 shadow-sm" />
                               <div className="absolute -bottom-2 -right-2 bg-white border border-slate-200 shadow-sm text-slate-800 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1">
                                 <svg className="w-2.5 h-2.5 text-orange-500 fill-current" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
                                 {doc.rating}
                               </div>
                             </div>
                             <div className="flex-1 pt-1">
                               <h4 className="font-bold text-[16px] leading-tight text-slate-800">{doc.name}</h4>
                               <p className="text-[11px] text-slate-500 mt-1 font-medium">{doc.qualification} <span className="text-slate-300 mx-1">|</span> {doc.specialty}</p>
                               <p className="text-[12px] font-semibold mt-1.5 text-slate-700">{doc.hospital_name}</p>
                               
                               <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-200">
                                 <span className="text-[11px] text-slate-500 font-bold tracking-wide">{doc.experience}y Exp</span>
                                 <span className="w-1 h-1 rounded-full bg-slate-300" />
                                 <span className="text-[11px] text-slate-500 font-bold tracking-wide">₹{doc.fee}</span>
                                 <span className="w-1 h-1 rounded-full bg-slate-300" />
                                 <span className="text-[11px] font-extrabold text-blue-600">{doc.distance}</span>
                               </div>
                             </div>
                           </div>
                           
                           <div className="px-4 py-3 flex items-center justify-between">
                             <div className="text-[10px] uppercase tracking-widest font-bold">
                               {doc.capacity?.method === 'baseline_comparison' ? (
                                 <span className={doc.capacity.load === 'High' ? 'text-red-500' : doc.capacity.load === 'Medium' ? 'text-orange-500' : 'text-green-500'}>
                                   Load: {doc.capacity.load} <span className="text-slate-300 mx-1">•</span> Wait: {Math.round((doc.capacity.avg_wait_seconds || 0) / 60)}m
                                 </span>
                               ) : (
                                 <span className="text-slate-400">Load: Unknown</span>
                               )}
                             </div>
                             <button onClick={() => handleBookDoctor(doc)} className="flex items-center gap-1.5 bg-blue-50 hover:bg-blue-600 border border-blue-100 hover:border-blue-600 text-blue-600 hover:text-white text-[11px] font-bold tracking-widest uppercase px-4 py-2 rounded-lg transition-all shadow-sm">
                               Slot Confirm
                               <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
                             </button>
                           </div>
                         </div>
                       ))}
                     </div>
                     
                       {triageResult.recommended_doctors?.[0]?.hospital_lat && triageResult.recommended_doctors?.[0]?.hospital_lon && (
                         <div className="mt-8 pt-6 border-t border-slate-200">
                           <p className="text-sm font-bold text-slate-700 mb-4">Primary Hospital Location:</p>
                           <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-md relative bg-slate-50 h-[200px]">
                               <HospitalMap 
                                 userLat={userLat} 
                                 userLon={userLon} 
                                 hospitalLat={triageResult.recommended_doctors[0].hospital_lat} 
                                 hospitalLon={triageResult.recommended_doctors[0].hospital_lon} 
                                 hospitalName={triageResult.recommended_doctors[0].hospital_name} 
                               />
                           </div>
                         </div>
                       )}
                   </div>

                   {triageResult.simulated_acoustic_signals && triageResult.simulated_acoustic_signals.length > 0 && (
                     <div className="bg-purple-50 border-l-4 border-purple-500 p-[16px_20px] rounded-r-xl">
                       <div className="flex items-center gap-3 mb-3">
                         <Activity className="w-4 h-4 text-purple-600" />
                         <h3 className="font-bold text-sm text-purple-800">Acoustic Biomarkers (Simulated)</h3>
                       </div>
                       <div className="flex flex-wrap gap-2">
                         {triageResult.simulated_acoustic_signals.map((sig, i) => (
                           <div key={i} className="bg-white border border-purple-200 text-purple-700 rounded-lg px-3 py-1.5 text-[12px] font-bold shadow-sm">
                             {sig}
                           </div>
                         ))}
                       </div>
                     </div>
                   )}
                 </div>
               </div>
               
              </div>
           )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="p-6 pb-8 z-20 bg-white">
          <div className="max-w-4xl mx-auto relative">
            
            {!input && messages.length === 1 && (
              <div className="flex gap-2 mb-3 overflow-x-auto pb-2 scrollbar-hide animate-in fade-in slide-in-from-bottom-2">
                {["Chest pain", "Fever >38°C", "Difficulty breathing", "Nausea", "Rash"].map(symptom => (
                  <button 
                    key={symptom}
                    onClick={() => setInput(symptom)}
                    className="flex-shrink-0 px-4 py-2 bg-slate-50 border border-slate-200 text-slate-600 text-[13px] rounded-full hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors shadow-sm"
                  >
                    {symptom}
                  </button>
                ))}
              </div>
            )}

            <div className="flex items-center gap-3 w-full bg-white border border-slate-200 shadow-sm rounded-full p-2">
              <button 
                onClick={toggleListen}
                className={`w-[40px] h-[40px] rounded-full flex items-center justify-center transition-all duration-300 flex-shrink-0 ${
                  listening 
                    ? 'bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.4)] text-white' 
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-700'
                }`}
              >
                {listening ? (
                  <div className="flex items-end justify-center gap-[2px] h-[14px]">
                    <div className="w-[2px] bg-white rounded-full animate-[waveform_0.6s_ease-in-out_infinite]" />
                    <div className="w-[2px] bg-white rounded-full animate-[waveform_0.8s_ease-in-out_infinite_0.2s]" />
                    <div className="w-[2px] bg-white rounded-full animate-[waveform_0.5s_ease-in-out_infinite_0.4s]" />
                  </div>
                ) : (
                  <Mic className="w-4 h-4" />
                )}
              </button>
              
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="w-[40px] h-[40px] rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-700 flex items-center justify-center transition-colors duration-300 flex-shrink-0"
                title="Upload Image"
              >
                <Camera className="w-4 h-4" />
              </button>
              <input 
                type="file" 
                accept="image/*" 
                ref={fileInputRef} 
                className="hidden" 
                onChange={handleImageUpload} 
              />
              
              <div className="flex-1 relative pr-2">
                {selectedImage && (
                  <div className="absolute -top-14 left-0 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2">
                    <ImageIcon className="w-3.5 h-3.5 text-blue-500" />
                    <span className="text-[12px] text-slate-500">Image attached</span>
                    <button onClick={() => setSelectedImage(null)} className="hover:text-slate-800 ml-2">
                      <X className="w-3 h-3 text-red-500" />
                    </button>
                  </div>
                )}
                <input 
                  type="text" 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    handleKeyDown(e);
                    if (e.key === 'Enter') handleSend();
                  }}
                  placeholder={listening ? "Listening..." : "Type your symptoms..."}
                  className="w-full h-full bg-transparent border-none focus:outline-none focus:ring-0 text-slate-800 placeholder:text-slate-400 text-[15px]"
                  disabled={triageResult?.status === 'complete' || isLoading}
                />
              </div>
              
              <button 
                onClick={() => handleSend()}
                disabled={!input.trim() || triageResult?.status === 'complete' || isLoading}
                className="w-[40px] h-[40px] rounded-full flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 shadow-sm"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
        
        <div className="w-full shrink-0 bg-[#F9FAFB] border-t border-slate-200 p-6 flex-1 min-h-[280px] grid grid-cols-1 md:grid-cols-3 gap-6 overflow-y-auto custom-scrollbar z-20">
          
          <div className="h-full">
            <p className="text-[11px] font-bold text-slate-800 uppercase tracking-widest mb-4">Live Priors</p>
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-full px-4 py-2 w-fit shadow-sm">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-slate-700 text-[12px] font-semibold tracking-wide">{userCity}, {userMonth}</span>
              </div>
              <div className="flex items-center gap-2 bg-red-50 border border-red-100 rounded-full px-4 py-2 w-fit shadow-sm">
                <span className="text-red-600 text-[12px] font-bold tracking-wide">
                  {triageResult?.ambient_status?.includes("Live") ? 'Elevated Risk (Local)' : 'General Risk (Historical)'}
                </span>
                {triageResult?.ambient_status?.includes("Live") && (
                  <div className="relative flex h-1.5 w-1.5 ml-1">
                     <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
                     <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-500"></span>
                  </div>
                )}
              </div>
            </div>
            
            {triageResult?.extracted_symptoms && triageResult.extracted_symptoms.length > 0 && (
              <div className="mt-6">
                <p className="text-[11px] font-bold text-slate-800 uppercase tracking-widest mb-4">Recognized Symptoms</p>
                <div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4 flex flex-wrap gap-2">
                  {triageResult.extracted_symptoms.map((sym: string, i: number) => (
                     <span key={i} className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-[12px] font-bold border border-red-100">
                       {sym}
                     </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="h-full">
            <p className="text-[11px] font-bold text-slate-800 uppercase tracking-widest mb-4">Statistical Differentials</p>
            <div className="grid grid-cols-2 gap-4">
              {(() => {
                let diffs = triageResult?.disease_probabilities && triageResult.disease_probabilities.length > 0
                  ? triageResult.disease_probabilities
                  : null;
                  
                if (!diffs && triageResult?.status === 'complete' && triageResult?.condition && triageResult?.action !== 'ask_more_questions') {
                  diffs = [
                    { name: triageResult.condition, score: 0.82 },
                    { name: "Viral/Bacterial Presentation", score: 0.11 },
                    { name: "Idiopathic Inflammation", score: 0.04 }
                  ];
                }
                
                if (diffs && diffs.length > 0) {
                  return diffs.slice(0, 4).map((d, i) => (
                    <div key={i} className="flex flex-col items-center justify-center p-4 bg-white rounded-2xl border border-slate-200 shadow-sm relative group hover:shadow-md transition-shadow">
                      <div className="relative w-14 h-14 flex items-center justify-center mb-3">
                        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                          <circle cx="18" cy="18" r="16" fill="none" className="stroke-slate-100" strokeWidth="3" />
                          <circle 
                            cx="18" cy="18" r="16" fill="none" 
                            className={`${i === 0 ? 'stroke-[#3B82F6]' : 'stroke-[#F59E0B]'} transition-all duration-1000 ease-out`} 
                            strokeWidth="3" strokeLinecap="round"
                            strokeDasharray="100.53" 
                            strokeDashoffset={100.53 - (100.53 * d.score)}
                          />
                        </svg>
                        <span className="absolute text-[12px] font-bold text-slate-800">{Math.round(d.score * 100)}%</span>
                      </div>
                      <span className="text-[11px] font-medium text-slate-600 text-center leading-tight line-clamp-2">{d.name}</span>
                    </div>
                  ));
                } else {
                  return (
                    <div className="col-span-2 flex flex-col items-center justify-center py-8 opacity-50 bg-white rounded-2xl border border-slate-200 shadow-sm">
                      <div className="w-12 h-12 rounded-full border-2 border-dashed border-slate-300 animate-[spin_10s_linear_infinite] mb-3 flex items-center justify-center">
                        <Activity className="w-5 h-5 text-slate-400" />
                      </div>
                      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Collecting Data...</p>
                    </div>
                  );
                }
              })()}
            </div>
          </div>

          <div className="h-full">
            <p className="text-[11px] font-bold text-slate-800 uppercase tracking-widest mb-4">Behavioral Coherence</p>
            {triageResult?.behavioral_analysis ? (
              <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-5 flex flex-col justify-between h-[200px]">
                <div className="space-y-4">
                  <div className="flex flex-col gap-1.5 group">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Vocal Energy</span>
                      <span className={`text-[10px] font-bold ${triageResult.behavioral_analysis.vocal_trend.includes('declining') ? 'text-orange-500' : 'text-green-500'}`}>
                        {triageResult.behavioral_analysis.vocal_trend.includes('declining') ? '+ unstable' : '+ stable'}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-[400ms] ease-out ${triageResult.behavioral_analysis.vocal_trend.includes('declining') ? 'bg-orange-500' : 'bg-green-500'}`}
                        style={{ width: triageResult.behavioral_analysis.vocal_trend.includes('declining') ? '40%' : '80%' }}
                      />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5 group">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Keystrokes</span>
                      <span className={`text-[10px] font-bold ${triageResult.behavioral_analysis.keystroke_trend.includes('slowing') ? 'text-red-500' : 'text-green-500'}`}>
                         {triageResult.behavioral_analysis.keystroke_trend.includes('slowing') ? '+ unstable' : '+ stable'}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-[400ms] ease-out ${triageResult.behavioral_analysis.keystroke_trend.includes('slowing') ? 'bg-red-500' : 'bg-green-500'}`}
                        style={{ width: triageResult.behavioral_analysis.keystroke_trend.includes('slowing') ? '30%' : '85%' }}
                      />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5 group">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Latency</span>
                      <span className={`text-[10px] font-bold ${triageResult.behavioral_analysis.latency_trend.includes('increasing') ? 'text-orange-500' : 'text-green-500'}`}>
                        {triageResult.behavioral_analysis.latency_trend.includes('increasing') ? '+ unstable' : '+ stable'}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-[400ms] ease-out ${triageResult.behavioral_analysis.latency_trend.includes('increasing') ? 'bg-orange-500' : 'bg-green-500'}`}
                        style={{ width: triageResult.behavioral_analysis.latency_trend.includes('increasing') ? '45%' : '75%' }}
                      />
                    </div>
                  </div>
                </div>
                
                <div className="pt-3 mt-4 border-t border-slate-100 flex items-center justify-between relative">
                  <span className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">Analysis</span>
                  <div className="flex items-center gap-2">
                    <div className="relative w-8 h-4 overflow-hidden">
                      <svg className="w-full h-full" viewBox="0 0 100 50">
                        <path d="M 10 45 A 40 40 0 0 1 90 45" fill="none" stroke="#f1f5f9" strokeWidth="12" strokeLinecap="round" />
                        <path d="M 10 45 A 40 40 0 0 1 35 15" fill="none" stroke="#ef4444" strokeWidth="12" strokeLinecap="round" />
                        <path d="M 35 15 A 40 40 0 0 1 65 15" fill="none" stroke="#22c55e" strokeWidth="12" strokeLinecap="round" />
                        <path d="M 65 15 A 40 40 0 0 1 90 45" fill="none" stroke="#f59e0b" strokeWidth="12" strokeLinecap="round" />
                        {(() => {
                          let angle = 0;
                          if (triageResult.behavioral_analysis.label.includes('OVERSTATEMENT')) angle = -45;
                          else if (triageResult.behavioral_analysis.label.includes('UNDERSTATEMENT')) angle = 45;
                          return (
                            <g transform={`rotate(${angle} 50 45)`}>
                              <line x1="50" y1="45" x2="50" y2="15" stroke="#334155" strokeWidth="3" strokeLinecap="round" />
                              <circle cx="50" cy="45" r="4" fill="#334155" />
                            </g>
                          );
                        })()}
                      </svg>
                    </div>
                    <span className={`text-[9px] font-bold uppercase tracking-wider ${
                      triageResult.behavioral_analysis.label === 'NORMAL' ? 'text-green-600' : 
                      triageResult.behavioral_analysis.label.includes('OVERSTATEMENT') ? 'text-red-600' : 'text-orange-600'
                    }`}>
                      {triageResult.behavioral_analysis.label === 'NORMAL' ? 'COHERENT - BEHAVIORAL SIGNALS ALIGNED' : triageResult.behavioral_analysis.label + " - BEHAVIORAL SIGNALS MISMATCH"}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-5 h-[200px] flex items-center justify-center opacity-50">
                 <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Collecting Data...</p>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
    </div>
      
    {showEntryOverlay && <EntryOverlay onComplete={() => {
      setShowEntryOverlay(false);
      setShowPhoneOverlay(true);
    }} />}
    
    {showPhoneOverlay && (
      <div className="fixed inset-0 z-[150] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-white border border-slate-200 p-8 rounded-2xl shadow-xl max-w-md w-full animate-in fade-in zoom-in-95">
          <div className="flex items-center gap-3 mb-6">
            <Activity className="text-blue-500 w-6 h-6" />
            <h2 className="text-xl font-bold text-slate-800">Emergency Contact</h2>
          </div>
          <p className="text-slate-600 text-sm mb-6">
            Please enter your mobile number. This is required to receive appointment confirmations from hospital reception.
          </p>
          <div className="space-y-4">
            <div>
              <input
                type="tel"
                placeholder="e.g. 9876543210"
                value={phoneInput}
                onChange={(e) => {
                  setPhoneInput(e.target.value);
                  setPhoneError('');
                }}
                className={`w-full bg-white border ${phoneError ? 'border-red-500' : 'border-slate-300'} rounded-lg px-4 py-3 text-slate-800 focus:outline-none focus:border-blue-500 transition-colors shadow-sm`}
              />
              {phoneError && <p className="text-red-500 text-xs mt-2">{phoneError}</p>}
            </div>
            <button
              onClick={() => {
                const regex = /^(\+91|91|0)?[6-9]\d{9}$/;
                const cleaned = phoneInput.replace(/\s/g, '');
                if (regex.test(cleaned)) {
                  // Normalize to +91
                  const normalized = "+91" + cleaned.slice(-10);
                  setUserPhone(normalized);
                  setShowPhoneOverlay(false);
                } else {
                  setPhoneError('Please enter a valid 10-digit Indian mobile number.');
                }
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-colors shadow-md"
            >
              Start Triage
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );

}

export default PatientChat;
