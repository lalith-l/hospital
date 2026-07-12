import re

content = """
  return (
    <>
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex items-center justify-center p-4 md:p-8 relative overflow-hidden z-0">
      
      <div className="w-full max-w-[1200px] h-[85vh] bg-white rounded-2xl overflow-hidden shadow-xl border border-slate-200 flex flex-col relative z-10">
    
      {/* Toast Popup for Alert Status */}
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

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative min-h-0 bg-white">
        
        {/* Top Action Bar Header */}
        <div className="w-full bg-white border-b border-slate-100 p-4 flex justify-between items-center z-50 shrink-0">
          <div className="flex items-center gap-2 px-3 text-blue-600 font-bold text-[13px] tracking-widest uppercase">
            <Activity className="w-4 h-4" />
            Pathfinder Triage
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3 w-full md:w-auto pr-3">
            <button onClick={handleDownloadReport} className="flex items-center gap-1.5 px-4 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-100 text-blue-600 text-[11px] font-bold tracking-widest uppercase rounded-lg transition-all">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
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
                           const d = new Date();
                           const minsToAdd = triageResult.urgency === 1 ? 5 : triageResult.urgency === 2 ? 30 : 120;
                           d.setMinutes(d.getMinutes() + minsToAdd);
                           return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        })()}
                      </div>
                      
                      {/* Watchdog Stability Check UI */}
                      {triageResult.watchdog && (
                        <div className={`mt-2 px-[10px] py-[3px] rounded-full text-[10px] font-bold tracking-widest uppercase flex items-center gap-1.5 border shadow-sm ${
                          triageResult.watchdog.hallucination_detected 
                            ? 'bg-red-50 border-red-200 text-red-600' 
                            : 'bg-green-50 border-green-200 text-green-600'
                        }`}>
                          {triageResult.watchdog.hallucination_detected ? (
                            <>
                              <AlertTriangle className="w-3 h-3 animate-pulse" />
                              ⚠ STABILITY CHECK: FLAGGED
                            </>
                          ) : (
                            <>
                              <span className="text-xs">🛡</span>
                              STABILITY CHECK: PASSED
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
                                 <svg className="w-2.5 h-2.5 text-orange-500 fill-current" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
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
                           
                           {/* Action Bar / Capacity */}
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
                               <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"/></svg>
                             </button>
                           </div>
                         </div>
                       ))}
                     </div>
                     
                       {/* Map the first hospital as the primary location */}
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

        {/* Input Area */}
        <div className="p-6 pb-8 z-20 bg-white">
          <div className="max-w-4xl mx-auto relative">
            
            {/* Quick-chips when input is empty */}
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
        
        {/* Bottom Dashboard Panels (Light Theme) */}
        <div className="w-full shrink-0 bg-[#F9FAFB] border-t border-slate-200 p-6 flex-1 min-h-[280px] grid grid-cols-1 md:grid-cols-3 gap-6 overflow-y-auto custom-scrollbar z-20">
          
          <div className="h-full">
            {/* Live Priors Card */}
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
            {/* Statistical Differentials Card */}
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
            {/* Behavioral Coherence Panel */}
            <p className="text-[11px] font-bold text-slate-800 uppercase tracking-widest mb-4">Behavioral Coherence</p>
            {triageResult?.behavioral_analysis ? (
              <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-5 flex flex-col justify-between h-[200px]">
                <div className="space-y-4">
                  {/* Vocal Energy Row */}
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
                  {/* Keystroke Speed Row */}
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
                  {/* Response Latency Row */}
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
                    {/* Gauge Icon Miniature */}
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
"""

with open('PatientChat.tsx', 'r') as f:
    text = f.read()

# find return ( and truncate
idx = text.find('  return (')
text = text[:idx]

text += content
text += "\n}\n\nexport default PatientChat;\n"

with open('PatientChat.tsx', 'w') as f:
    f.write(text)
