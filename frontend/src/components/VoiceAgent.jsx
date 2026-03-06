import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../App";
import { Button } from "./ui/button";
import { toast } from "sonner";
import { Mic, MicOff, Volume2, Loader2, X, MessageSquare, ArrowRight, ChevronRight } from "lucide-react";

const VoiceAgent = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState(null);
  const [matchedRFQs, setMatchedRFQs] = useState([]);
  const [totalMatches, setTotalMatches] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);

  useEffect(() => {
    // Prevent body scroll when modal is open
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    return () => {
      document.body.style.overflow = 'unset';
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, [isOpen]);

  const handleClose = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsListening(false);
    setIsSpeaking(false);
    setTranscript("");
    setResponse(null);
    setMatchedRFQs([]);
    onClose();
  };

  const handleViewRFQ = (rfqId) => {
    handleClose();
    navigate(`/vendor/rfq/${rfqId}`);
  };

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      audioChunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        await processAudio(audioBlob);
      };
      
      mediaRecorderRef.current.start();
      setIsListening(true);
      setTranscript("");
      setResponse(null);
      
    } catch (error) {
      console.error("Microphone error:", error);
      toast.error("Could not access microphone. Please allow microphone access.");
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsListening(false);
    }
  };

  const processAudio = async (audioBlob) => {
    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      
      const transcribeResponse = await api.post('/voice/transcribe', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const userQuery = transcribeResponse.data.text;
      const detectedLanguage = transcribeResponse.data.language || 'en';
      setTranscript(userQuery);
      
      if (!userQuery || userQuery.trim().length < 2) {
        toast.error("Could not understand. Please try again.");
        setIsProcessing(false);
        return;
      }
      
      const queryResponse = await api.post('/voice/query', {
        query: userQuery,
        language: detectedLanguage
      });
      
      setResponse(queryResponse.data.response_text);
      setMatchedRFQs(queryResponse.data.matched_rfqs || []);
      setTotalMatches(queryResponse.data.total_matches || 0);
      
      if (queryResponse.data.audio_base64) {
        playAudioResponse(queryResponse.data.audio_base64);
      }
      
    } catch (error) {
      console.error("Voice processing error:", error);
      toast.error(error.response?.data?.detail || "Voice processing failed");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleQuickQuery = async (query, lang = 'en') => {
    setTranscript(query);
    setIsProcessing(true);
    try {
      const queryResponse = await api.post('/voice/query', { query, language: lang });
      setResponse(queryResponse.data.response_text);
      setMatchedRFQs(queryResponse.data.matched_rfqs || []);
      setTotalMatches(queryResponse.data.total_matches || 0);
      if (queryResponse.data.audio_base64) {
        playAudioResponse(queryResponse.data.audio_base64);
      }
    } catch (err) {
      toast.error("Query failed");
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudioResponse = (base64Audio) => {
    try {
      setIsSpeaking(true);
      const audioData = atob(base64Audio);
      const audioArray = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
      }
      const audioBlob = new Blob([audioArray], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      if (audioRef.current) audioRef.current.pause();
      
      audioRef.current = new Audio(audioUrl);
      audioRef.current.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
      audioRef.current.onerror = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
      audioRef.current.play();
    } catch (error) {
      setIsSpeaking(false);
    }
  };

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsSpeaking(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center"
      data-testid="voice-agent-modal"
    >
      {/* Mobile-optimized full-screen modal */}
      <div className="w-full h-full sm:h-auto sm:max-h-[90vh] sm:max-w-lg bg-white sm:rounded-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-300">
        
        {/* Header with Close Button */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4 sm:p-5 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Voice Assistant</h2>
                <p className="text-orange-100 text-xs">English, Hindi & Indian languages</p>
              </div>
            </div>
            
            {/* Close Button - Always Visible */}
            <button
              onClick={handleClose}
              className="w-10 h-10 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-colors"
              data-testid="voice-agent-close-btn"
            >
              <X className="w-6 h-6 text-white" />
            </button>
          </div>
        </div>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          
          {/* Microphone Button */}
          <div className="flex flex-col items-center py-4">
            <button
              onClick={isListening ? stopListening : startListening}
              disabled={isProcessing}
              className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg ${
                isListening 
                  ? "bg-red-500 hover:bg-red-600 animate-pulse shadow-red-200" 
                  : isProcessing
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-orange-500 hover:bg-orange-600 hover:scale-105 shadow-orange-200"
              }`}
              data-testid="voice-mic-button"
            >
              {isProcessing ? (
                <Loader2 className="w-8 h-8 sm:w-10 sm:h-10 text-white animate-spin" />
              ) : isListening ? (
                <MicOff className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
              ) : (
                <Mic className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
              )}
            </button>
            <p className="text-sm text-gray-500 mt-3 text-center">
              {isListening ? "Listening... Tap to stop" : isProcessing ? "Processing..." : "Tap to speak"}
            </p>
          </div>

          {/* Transcript */}
          {transcript && (
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">You said</p>
              <p className="text-gray-800">{transcript}</p>
            </div>
          )}

          {/* AI Response */}
          {response && (
            <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-orange-500 uppercase tracking-wide font-medium">Assistant</p>
                {isSpeaking && (
                  <button 
                    onClick={stopSpeaking}
                    className="flex items-center gap-1 text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded-full"
                  >
                    <Volume2 className="w-3 h-3 animate-pulse" /> Stop
                  </button>
                )}
              </div>
              <p className="text-gray-800 leading-relaxed">{response}</p>
            </div>
          )}

          {/* RFQ Results */}
          {matchedRFQs.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-800">Open RFQs</h3>
                <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded-full">
                  {totalMatches} opportunities
                </span>
              </div>
              
              <div className="space-y-2">
                {matchedRFQs.map((rfq) => (
                  <button
                    key={rfq.rfq_id}
                    onClick={() => handleViewRFQ(rfq.rfq_id)}
                    className="w-full bg-white border border-gray-200 rounded-xl p-4 text-left hover:border-orange-300 hover:shadow-md transition-all group"
                    data-testid={`rfq-link-${rfq.rfq_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-gray-800 truncate group-hover:text-orange-600">
                          {rfq.title}
                        </h4>
                        <p className="text-sm text-gray-500 mt-0.5">
                          {rfq.material} • Qty: {rfq.quantity}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 ml-3">
                        <span className={`px-2 py-1 rounded-lg text-xs font-semibold ${
                          rfq.match_score >= 70 
                            ? "bg-green-100 text-green-700" 
                            : rfq.match_score >= 50 
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-600"
                        }`}>
                          {rfq.match_score}%
                        </span>
                        <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-orange-500 group-hover:translate-x-1 transition-all" />
                      </div>
                    </div>
                  </button>
                ))}
              </div>
              
              {/* View All Button */}
              <button
                onClick={() => { handleClose(); navigate('/vendor/matched-rfqs'); }}
                className="w-full py-3 text-center text-orange-600 hover:text-orange-700 font-medium border border-orange-200 rounded-xl hover:bg-orange-50 transition-colors"
              >
                View All Matched RFQs →
              </button>
            </div>
          )}

          {/* Quick Questions */}
          {!response && !isProcessing && (
            <div className="pt-2">
              <p className="text-xs text-gray-400 mb-3 uppercase tracking-wide">Quick Questions</p>
              <div className="space-y-2">
                {[
                  { text: "What open RFQs can I quote?", lang: "en" },
                  { text: "मेरे लिए कौन से RFQ हैं?", lang: "hi" },
                  { text: "Show high priority matches", lang: "en" },
                ].map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuickQuery(q.text, q.lang)}
                    className="w-full text-left text-sm bg-gray-50 hover:bg-gray-100 text-gray-700 px-4 py-3 rounded-xl transition-colors border border-gray-100"
                  >
                    "{q.text}"
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Bottom Close Button for Mobile */}
        <div className="flex-shrink-0 p-4 border-t bg-gray-50 sm:hidden">
          <Button
            onClick={handleClose}
            variant="outline"
            className="w-full py-6 text-base font-medium"
          >
            <X className="w-5 h-5 mr-2" /> Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default VoiceAgent;
