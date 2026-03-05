import { useState, useRef, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { toast } from "sonner";
import { Mic, MicOff, Volume2, Loader2, X, MessageSquare } from "lucide-react";

const VoiceAgent = ({ isOpen, onClose }) => {
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
      // Step 1: Transcribe audio
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      
      const transcribeResponse = await api.post('/voice/transcribe', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const userQuery = transcribeResponse.data.text;
      setTranscript(userQuery);
      
      if (!userQuery || userQuery.trim().length < 2) {
        toast.error("Could not understand. Please try again.");
        setIsProcessing(false);
        return;
      }
      
      // Step 2: Process query and get response
      const queryResponse = await api.post('/voice/query', {
        query: userQuery
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="voice-agent-modal">
      <Card className="w-full max-w-lg bg-white shadow-2xl">
        <CardHeader className="bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-t-lg">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Voice Assistant
            </CardTitle>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onClose}
              className="text-white hover:bg-white/20"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
          <p className="text-orange-100 text-sm mt-1">
            Ask about your matched RFQs
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

          {/* Matched RFQs Summary */}
          {matchedRFQs.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Your Matched RFQs:</p>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {matchedRFQs.map((rfq, index) => (
                  <div 
                    key={rfq.rfq_id} 
                    className="bg-white border rounded-lg p-3 text-sm hover:border-orange-300 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-800 truncate flex-1">
                        {rfq.title}
                      </span>
                      <span className={`ml-2 px-2 py-0.5 rounded-full text-xs font-medium ${
                        rfq.match_score >= 70 
                          ? "bg-green-100 text-green-700" 
                          : rfq.match_score >= 50 
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-gray-100 text-gray-600"
                      }`}>
                        {rfq.match_score}%
                      </span>
                    </div>
                    <p className="text-gray-500 text-xs mt-1">
                      {rfq.material} • Qty: {rfq.quantity}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sample Questions */}
          <div className="border-t pt-4">
            <p className="text-xs text-gray-500 mb-2">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {[
                "What new RFQs match my machines?",
                "Show me high-priority opportunities",
                "Any urgent requests today?"
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setTranscript(suggestion);
                    api.post('/voice/query', { query: suggestion })
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
