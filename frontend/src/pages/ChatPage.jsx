import { useState, useEffect, useRef } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Send, ArrowLeft, MessageSquare, Loader2, 
  User, Building2, FileText
} from "lucide-react";

const ChatPage = () => {
  const { conversationId } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  const otherUserId = searchParams.get("with");
  const rfqId = searchParams.get("rfq");

  useEffect(() => {
    fetchConversations();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (conversationId) {
      fetchConversationMessages(conversationId);
    } else if (otherUserId) {
      startConversation(otherUserId, rfqId);
    }
  }, [conversationId, otherUserId, rfqId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Poll for new messages every 5 seconds
  useEffect(() => {
    if (!activeConversation) return;
    
    const interval = setInterval(() => {
      fetchConversationMessages(activeConversation.conversation_id, true);
    }, 5000);

    return () => clearInterval(interval);
  }, [activeConversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchConversations = async () => {
    try {
      const response = await api.get("/messages/conversations");
      setConversations(response.data);
    } catch (error) {
      console.error("Failed to load conversations");
    } finally {
      setLoading(false);
    }
  };

  const fetchConversationMessages = async (convId, silent = false) => {
    try {
      const response = await api.get(`/messages/conversation/${convId}`);
      setActiveConversation(response.data.conversation);
      setMessages(response.data.messages);
      if (!silent) {
        fetchConversations(); // Refresh sidebar
      }
    } catch (error) {
      if (!silent) toast.error("Failed to load messages");
    }
  };

  const startConversation = async (userId, rfq = null) => {
    try {
      const params = rfq ? `?rfq_id=${rfq}` : "";
      const response = await api.get(`/messages/with/${userId}${params}`);
      setActiveConversation(response.data.conversation);
      setMessages(response.data.messages);
      fetchConversations();
    } catch (error) {
      toast.error("Failed to start conversation");
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeConversation) return;

    setSending(true);
    try {
      const otherPartyId = activeConversation.participants.find(p => p !== user.user_id);
      await api.post("/messages", {
        receiver_id: otherPartyId,
        rfq_id: activeConversation.rfq_id,
        content: newMessage.trim()
      });
      
      setNewMessage("");
      fetchConversationMessages(activeConversation.conversation_id, true);
    } catch (error) {
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return "Yesterday";
    } else if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="h-[calc(100vh-180px)] flex gap-4" data-testid="chat-page">
        {/* Conversations Sidebar */}
        <Card className="w-80 flex-shrink-0 border-slate-200 flex flex-col">
          <CardHeader className="py-4 border-b">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-orange-600" /> Messages
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 overflow-y-auto">
            {conversations.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {conversations.map((conv) => (
                  <button
                    key={conv.conversation_id}
                    onClick={() => fetchConversationMessages(conv.conversation_id)}
                    className={`w-full p-4 text-left hover:bg-slate-50 transition-colors ${
                      activeConversation?.conversation_id === conv.conversation_id ? "bg-orange-50" : ""
                    }`}
                    data-testid={`conv-${conv.conversation_id}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        conv.other_party?.role === "vendor" ? "bg-slate-200" : "bg-blue-100"
                      }`}>
                        {conv.other_party?.role === "vendor" ? (
                          <Building2 className="w-5 h-5 text-slate-600" />
                        ) : (
                          <User className="w-5 h-5 text-blue-600" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-slate-900 truncate">
                            {conv.other_party?.name}
                          </p>
                          <span className="text-xs text-slate-400">
                            {formatTime(conv.last_message_at)}
                          </span>
                        </div>
                        {conv.rfq_title && (
                          <p className="text-xs text-orange-600 truncate">
                            RE: {conv.rfq_title}
                          </p>
                        )}
                        <p className="text-sm text-slate-500 truncate">
                          {conv.last_message || "No messages yet"}
                        </p>
                        {conv.unread_count > 0 && (
                          <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-orange-600 rounded-full mt-1">
                            {conv.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-slate-500">
                <MessageSquare className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                <p>No conversations yet</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Chat Area */}
        <Card className="flex-1 border-slate-200 flex flex-col">
          {activeConversation ? (
            <>
              {/* Chat Header */}
              <CardHeader className="py-4 border-b flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    activeConversation.other_party?.role === "vendor" ? "bg-slate-200" : "bg-blue-100"
                  }`}>
                    {activeConversation.other_party?.role === "vendor" ? (
                      <Building2 className="w-5 h-5 text-slate-600" />
                    ) : (
                      <User className="w-5 h-5 text-blue-600" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">
                      {activeConversation.other_party?.name}
                    </p>
                    {activeConversation.rfq_id && (
                      <Link 
                        to={`/buyer/rfq/${activeConversation.rfq_id}`}
                        className="text-xs text-orange-600 hover:underline flex items-center gap-1"
                      >
                        <FileText className="w-3 h-3" /> View RFQ
                      </Link>
                    )}
                  </div>
                </div>
              </CardHeader>

              {/* Messages */}
              <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg) => {
                  const isOwn = msg.sender_id === user.user_id;
                  return (
                    <div
                      key={msg.message_id}
                      className={`flex ${isOwn ? "justify-end" : "justify-start"}`}
                    >
                      <div className={`max-w-[70%] ${isOwn ? "order-2" : ""}`}>
                        <div
                          className={`px-4 py-2 rounded-2xl ${
                            isOwn
                              ? "bg-orange-600 text-white rounded-br-sm"
                              : "bg-slate-100 text-slate-900 rounded-bl-sm"
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        </div>
                        <p className={`text-xs text-slate-400 mt-1 ${isOwn ? "text-right" : ""}`}>
                          {formatTime(msg.created_at)}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </CardContent>

              {/* Message Input */}
              <div className="p-4 border-t flex-shrink-0">
                <form onSubmit={sendMessage} className="flex gap-2">
                  <Input
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type your message..."
                    className="flex-1"
                    data-testid="message-input"
                  />
                  <Button 
                    type="submit" 
                    disabled={sending || !newMessage.trim()}
                    className="bg-orange-600 hover:bg-orange-700"
                    data-testid="send-message-btn"
                  >
                    {sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </form>
              </div>
            </>
          ) : (
            <CardContent className="flex-1 flex items-center justify-center">
              <div className="text-center text-slate-500">
                <MessageSquare className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <p className="text-lg font-medium">Select a conversation</p>
                <p className="text-sm">or start a new chat from a vendor profile</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default ChatPage;
