import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { toast } from "sonner";
import { Mic, MicOff, Volume2, Loader2, X, MessageSquare, ExternalLink, ArrowRight } from "lucide-react";

const VoiceAgent = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState(null);
  const [matchedRFQs, setMatchedRFQs] = useState([]);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // Handle close - cleanup and close
  const handleClose = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsListening(false);
    setIsSpeaking(false);
    onClose();
  };

  // Navigate to RFQ detail
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
      // Step 1: Transcribe audio (auto-detects language)
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
      
      // Step 2: Process query with detected language
      const queryResponse = await api.post('/voice/query', {
        query: userQuery,
        language: detectedLanguage
      });
      
      setResponse(queryResponse.data.response_text);
      setMatchedRFQs(queryResponse.data.matched_rfqs || []);
      
      // Step 3: Play audio response
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
      
      if (audioRef.current) {
        audioRef.current.pause();
      }
      
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
      console.error("Audio playback error:", error);
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
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm" 
      data-testid="voice-agent-modal"
      onClick={(e) => e.target === e.currentTarget && handleClose()}
    >
      <Card className="w-full max-w-lg bg-white shadow-2xl relative">
        {/* Close Button - Top Right Corner */}
        <button
          onClick={handleClose}
          className="absolute -top-3 -right-3 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-100 transition-colors z-10 border border-gray-200"
          data-testid="voice-agent-close-btn"
        >
          <X className="w-5 h-5 text-gray-600" />
        </button>
        
        <CardHeader className="bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-t-lg">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Voice Assistant
            </CardTitle>
          </div>
          <p className="text-orange-100 text-sm mt-1">
            Speak in English, Hindi, Tamil, Telugu, or any Indian language
          </p>
        </CardHeader>
        
        <CardContent className="p-6 space-y-6">
          {/* Microphone Button */}
          <div className="flex flex-col items-center gap-4">
            <button
              onClick={isListening ? stopListening : startListening}
              disabled={isProcessing}
              className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${
                isListening 
                  ? "bg-red-500 hover:bg-red-600 animate-pulse" 
                  : isProcessing
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-orange-500 hover:bg-orange-600 hover:scale-105"
              }`}
              data-testid="voice-mic-button"
            >
              {isProcessing ? (
                <Loader2 className="w-10 h-10 text-white animate-spin" />
              ) : isListening ? (
                <MicOff className="w-10 h-10 text-white" />
              ) : (
                <Mic className="w-10 h-10 text-white" />
              )}
            </button>
            
            <p className="text-sm text-gray-600">
              {isListening 
                ? "Listening... Click to stop" 
                : isProcessing 
                  ? "Processing your request..."
                  : "Click to start speaking"}
            </p>
          </div>

          {/* Transcript */}
          {transcript && (
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 mb-1">You said:</p>
              <p className="text-gray-800">{transcript}</p>
            </div>
          )}

          {/* Response */}
          {response && (
            <div className="bg-orange-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-orange-600 font-medium">Assistant:</p>
                {isSpeaking ? (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={stopSpeaking}
                    className="text-orange-600 h-6 px-2"
                  >
                    <Volume2 className="w-4 h-4 mr-1 animate-pulse" />
                    Stop
                  </Button>
                ) : null}
              </div>
              <p className="text-gray-800">{response}</p>
            </div>
          )}

          {/* Matched RFQs Summary with Links */}
          {matchedRFQs.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-700">Your Matched RFQs:</p>
                <span className="text-xs text-gray-500">{matchedRFQs.length} results</span>
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {matchedRFQs.map((rfq, index) => (
                  <div 
                    key={rfq.rfq_id} 
                    className="bg-white border rounded-lg p-3 text-sm hover:border-orange-400 hover:shadow-md transition-all cursor-pointer group"
                    onClick={() => handleViewRFQ(rfq.rfq_id)}
                    data-testid={`rfq-link-${rfq.rfq_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-800 truncate flex-1 group-hover:text-orange-600">
                        {rfq.title}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          rfq.match_score >= 70 
                            ? "bg-green-100 text-green-700" 
                            : rfq.match_score >= 50 
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-600"
                        }`}>
                          {rfq.match_score}%
                        </span>
                        <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-orange-500 group-hover:translate-x-1 transition-all" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-gray-500 text-xs">
                        {rfq.material} • Qty: {rfq.quantity}
                      </p>
                      <span className="text-xs text-orange-500 opacity-0 group-hover:opacity-100 transition-opacity">
                        View Details
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* View All Link */}
              <button
                onClick={() => { handleClose(); navigate('/vendor/matched-rfqs'); }}
                className="w-full text-center text-sm text-orange-600 hover:text-orange-700 font-medium py-2 border-t flex items-center justify-center gap-1"
              >
                View All Matched RFQs <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Sample Questions - English & Hindi */}
          <div className="border-t pt-4">
            <p className="text-xs text-gray-500 mb-2">Try asking (English or Hindi):</p>
            <div className="flex flex-wrap gap-2">
              {[
                "What new RFQs match my machines?",
                "मेरी मशीनों से कौन से RFQ मिलते हैं?",
                "Show me high-priority opportunities",
                "आज कोई urgent काम है?"
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setTranscript(suggestion);
                    const lang = suggestion.match(/[अ-ह]/) ? 'hi' : 'en';
                    api.post('/voice/query', { query: suggestion, language: lang })
                      .then(res => {
                        setResponse(res.data.response_text);
                        setMatchedRFQs(res.data.matched_rfqs || []);
                        if (res.data.audio_base64) {
                          playAudioResponse(res.data.audio_base64);
                        }
                      })
                      .catch(err => toast.error("Query failed"));
                  }}
                  className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-full transition-colors"
                >
                  "{suggestion}"
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default VoiceAgent;
