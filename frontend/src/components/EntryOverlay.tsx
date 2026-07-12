import React, { useState, useEffect, useRef } from 'react';

interface EntryOverlayProps {
  onComplete: () => void;
}

export const EntryOverlay: React.FC<EntryOverlayProps> = ({ onComplete }) => {
  const [isRevealing, setIsRevealing] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [dragY, setDragY] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [touchStartY, setTouchStartY] = useState<number | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if mobile
    setIsMobile(window.innerWidth <= 768);
    
    const timer = setTimeout(() => {
      setShowHint(true);
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  const triggerReveal = () => {
    setIsRevealing(true);
    setTimeout(() => {
      onComplete();
    }, 600); // 400ms for split, 600ms for app fade in
  };

  // --- Mouse / Pointer Dragging Logic ---
  const handlePointerDown = (e: React.PointerEvent) => {
    if (isRevealing || isMobile) return;
    setIsDragging(true);
    setDragY(e.clientY);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging || isRevealing || isMobile) return;
    
    // Only allow dragging downwards
    const windowHeight = window.innerHeight;
    const baseY = windowHeight * 0.52; // 52vh
    
    if (e.clientY > baseY) {
      setDragY(e.clientY);
      
      // Check if dragged past 72vh
      if (e.clientY > windowHeight * 0.72) {
        setIsDragging(false);
        triggerReveal();
      }
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isRevealing || isMobile) return;
    setIsDragging(false);
    setDragY(null); // snap back
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  // --- Mobile Touch Swipe Up Logic ---
  const handleTouchStart = (e: React.TouchEvent) => {
    if (isRevealing || !isMobile) return;
    setTouchStartY(e.touches[0].clientY);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (isRevealing || !isMobile || touchStartY === null) return;
    
    const currentY = e.touches[0].clientY;
    const deltaY = touchStartY - currentY; // positive means swiped up
    
    if (deltaY > 40) { // threshold
      setTouchStartY(null);
      triggerReveal();
    }
  };

  const handleTouchEnd = () => {
    setTouchStartY(null);
  };

  // Calculate current thread height
  const windowHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
  const baseHeight = windowHeight * 0.52;
  const currentHeight = dragY !== null ? Math.max(baseHeight, dragY) : baseHeight;

  return (
    <div 
      ref={containerRef}
      className={`fixed inset-0 z-[200] bg-[#000000] flex justify-center overflow-hidden font-sans select-none touch-none ${
        isRevealing ? 'pointer-events-none' : ''
      }`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* The Thread Elements */}
      <div 
        className="absolute top-0 flex flex-col items-center"
        style={{
          transform: isRevealing ? 'translateX(-50vw)' : 'translateX(0)',
          transition: isRevealing ? 'transform 400ms cubic-bezier(0.4, 0, 0, 1)' : 'none',
        }}
      >
        {/* Left half of the thread (only visible during split, otherwise it overlays perfectly) */}
        {isRevealing && (
          <div className="absolute top-0 flex flex-col items-center">
            <div 
              className="w-[2px] bg-[#E53935]" 
              style={{ height: `${currentHeight}px` }} 
            />
            <div className="w-[8px] h-[14px] bg-[#E53935] rounded-b-full rounded-t-[40%] mt-[-2px] shadow-[0_0_12px_2px_rgba(229,57,53,0.5)]" />
          </div>
        )}
      </div>

      <div 
        className="absolute top-0 flex flex-col items-center"
        style={{
          transform: isRevealing ? 'translateX(50vw)' : 'translateX(0)',
          transition: isRevealing ? 'transform 400ms cubic-bezier(0.4, 0, 0, 1)' : 'none',
        }}
      >
        {/* Main/Right thread */}
        <div 
          className="flex flex-col items-center w-[120px] cursor-grab active:cursor-grabbing"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          style={{ animation: !isDragging && !isRevealing ? 'thread-pulse 2s ease-in-out infinite' : 'none' }}
        >
          {/* Line */}
          <div 
            className="w-[2px] bg-[#E53935] relative" 
            style={{ 
              height: `${currentHeight}px`,
              transition: isDragging ? 'none' : 'height 300ms cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            {/* Bottom 20% glow */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[2px] h-[20%] shadow-[0_0_12px_3px_rgba(229,57,53,0.5)]" />
          </div>
          
          {/* Teardrop tip */}
          <div 
            className="w-[8px] h-[14px] bg-[#E53935] rounded-b-full rounded-t-[40%] mt-[-2px] shadow-[0_0_12px_2px_rgba(229,57,53,0.5)]"
            style={{
              transition: isDragging ? 'none' : 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          />

          {/* Hint text */}
          <div 
            className="absolute whitespace-nowrap text-[#ffffff44] text-[11px] uppercase tracking-[0.15em] pointer-events-none transition-all duration-1000"
            style={{ 
              top: `${currentHeight + 24}px`,
              opacity: showHint && !isDragging && !isRevealing ? 1 : 0 
            }}
          >
            {isMobile ? "swipe up to begin" : "pull to begin"}
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes thread-pulse {
          0% { opacity: 0.7; }
          50% { opacity: 1.0; }
          100% { opacity: 0.7; }
        }
      `}} />
    </div>
  );
};
