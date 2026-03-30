import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { 
  X, Send, Bot, User, Loader2, 
  Trash2, Minimize2, Maximize2, ThumbsUp, ThumbsDown
} from "lucide-react";

const API_URL = window.location.origin;

// Simple markdown parser for chat messages
const parseMarkdown = (text) => {
  if (!text) return text;
  
  // Convert **bold** to <strong>
  let parsed = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Convert *italic* to <em>
  parsed = parsed.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Convert numbered lists (1. 2. 3. etc)
  parsed = parsed.replace(/^(\d+)\.\s+/gm, '<span class="font-medium text-orange-600">$1.</span> ');
  
  // Convert bullet points
  parsed = parsed.replace(/^[-•]\s+/gm, '<span class="text-orange-500 mr-1">•</span>');
  
  // Convert line breaks
  parsed = parsed.replace(/\n/g, '<br/>');
  
  return parsed;
};

const ChatbotWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      type: "bot",
      text: "Hey there! 👋 I'm OEMBot, your friendly assistant for all things manufacturing. How can I help you today?",
      timestamp: new Date(),
      chatId: null,
      feedback: null
    }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus();
    }
  }, [isOpen, isMinimized]);

  // Generate session ID on first open
  useEffect(() => {
    if (isOpen && !sessionId) {
      const stored = localStorage.getItem("oembot_session");
      if (stored) {
        setSessionId(stored);
      } else {
        const newSession = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setSessionId(newSession);
        localStorage.setItem("oembot_session", newSession);
      }
    }
  }, [isOpen, sessionId]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: `user_${Date.now()}`,
      type: "user",
      text: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const token = localStorage.getItem("token");
      const endpoint = token ? "/api/chatbot/chat/user" : "/api/chatbot/chat/guest";
      
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token && { "Authorization": `Bearer ${token}` })
        },
        body: JSON.stringify({
          message: userMessage.text,
          session_id: sessionId
        })
      });

      const data = await response.json();

      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem("oembot_session", data.session_id);
      }

      const botMessage = {
        id: `bot_${Date.now()}`,
        type: "bot",
        text: data.response || "Sorry, I couldn't process that. Please try again!",
        timestamp: new Date(),
        chatId: data.chat_id,
        feedback: null
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = {
        id: `error_${Date.now()}`,
        type: "bot",
        text: "Oops! I'm having trouble connecting right now. Please try again or contact support@oemlinker.com 📧",
        timestamp: new Date(),
        chatId: null,
        feedback: null
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const submitFeedback = async (chatId, rating) => {
    if (!chatId) return;
    
    try {
      await fetch(`${API_URL}/api/chatbot/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, rating })
      });
      
      // Update message to show feedback was submitted
      setMessages(prev => prev.map(msg => 
        msg.chatId === chatId ? { ...msg, feedback: rating } : msg
      ));
    } catch (error) {
      console.error("Feedback error:", error);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    const newSession = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSession);
    localStorage.setItem("oembot_session", newSession);
    setMessages([
      {
        id: "welcome",
        type: "bot",
        text: "Chat cleared! 🧹 How can I help you today?",
        timestamp: new Date()
      }
    ]);
  };

  const quickQuestions = [
    "How does OEMLinker work?",
    "How do I create an RFQ?",
    "What manufacturing processes are supported?",
    "How is vendor matching done?"
  ];

  return (
    <>
      {/* Chat Toggle Button — fixed, no drag */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.92 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-5 left-5 z-50 w-12 h-12 md:w-14 md:h-14 rounded-full shadow-lg flex items-center justify-center bg-gradient-to-br from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 transition-all"
            data-testid="chatbot-toggle-btn"
          >
            <Bot className="w-6 h-6 md:w-7 md:h-7 text-white" />
            <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-white" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ 
              opacity: 1, 
              y: 0, 
              scale: 1,
              height: isMinimized ? "60px" : "min(500px, calc(100dvh - 100px))"
            }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-5 left-5 z-50 w-[min(380px,calc(100vw-40px))] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col"
            data-testid="chatbot-window"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-4 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">OEMBot</h3>
                  <p className="text-xs text-slate-400">
                    {isLoading ? "Typing..." : "Online"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={clearChat}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  title="Clear chat"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  title={isMinimized ? "Expand" : "Minimize"}
                >
                  {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  title="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {!isMinimized && (
              <>
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex flex-col ${message.type === "user" ? "items-end" : "items-start"}`}
                    >
                      <div className={`flex items-start gap-2 max-w-[85%] ${message.type === "user" ? "flex-row-reverse" : ""}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          message.type === "user" 
                            ? "bg-orange-500 text-white" 
                            : "bg-slate-200 text-slate-700"
                        }`}>
                          {message.type === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                        </div>
                        <div className={`rounded-2xl px-4 py-2 ${
                          message.type === "user"
                            ? "bg-orange-500 text-white rounded-br-md"
                            : "bg-white text-slate-700 border border-slate-200 rounded-bl-md shadow-sm"
                        }`}>
                          {message.type === "bot" ? (
                            <p 
                              className="text-sm leading-relaxed"
                              dangerouslySetInnerHTML={{ __html: parseMarkdown(message.text) }}
                            />
                          ) : (
                            <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                          )}
                        </div>
                      </div>
                      
                      {/* Feedback buttons for bot messages */}
                      {message.type === "bot" && message.chatId && (
                        <div className="flex items-center gap-1 mt-1 ml-10">
                          {message.feedback ? (
                            <span className="text-xs text-slate-400">
                              {message.feedback === 5 ? "👍 Thanks!" : "👎 We'll improve!"}
                            </span>
                          ) : (
                            <>
                              <button
                                onClick={() => submitFeedback(message.chatId, 5)}
                                className="p-1 hover:bg-green-100 rounded text-slate-400 hover:text-green-600 transition-colors"
                                title="Helpful"
                              >
                                <ThumbsUp className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => submitFeedback(message.chatId, 1)}
                                className="p-1 hover:bg-red-100 rounded text-slate-400 hover:text-red-600 transition-colors"
                                title="Not helpful"
                              >
                                <ThumbsDown className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ))}

                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex justify-start"
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
                          <Bot className="w-4 h-4 text-slate-700" />
                        </div>
                        <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Quick Questions (show only when few messages) */}
                {messages.length <= 2 && !isLoading && (
                  <div className="px-4 pb-2 flex flex-wrap gap-2">
                    {quickQuestions.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          setInputValue(q);
                          setTimeout(() => sendMessage(), 100);
                        }}
                        className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-full transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}

                {/* Input */}
                <div className="p-4 border-t border-slate-200 bg-white">
                  <div className="flex items-center gap-2">
                    <Input
                      ref={inputRef}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Type your message..."
                      disabled={isLoading}
                      className="flex-1 border-slate-200 focus:border-orange-400 focus:ring-orange-400"
                      data-testid="chatbot-input"
                    />
                    <Button
                      onClick={sendMessage}
                      disabled={!inputValue.trim() || isLoading}
                      size="icon"
                      className="bg-orange-500 hover:bg-orange-600 h-10 w-10"
                      data-testid="chatbot-send-btn"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-slate-400 mt-2 text-center">
                    Powered by AI • support@oemlinker.com
                  </p>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatbotWidget;
