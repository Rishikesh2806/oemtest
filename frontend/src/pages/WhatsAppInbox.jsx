import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { api } from '../App';
import { 
  MessageSquare, Send, Search, RefreshCw, Phone, User, Clock,
  ChevronLeft, ArrowUp, Check, CheckCheck, AlertCircle, Users,
  Inbox, MessageCircle, BarChart3, Megaphone, X
} from 'lucide-react';

export default function WhatsAppInbox() {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  
  // State
  const [stats, setStats] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [broadcastOpen, setBroadcastOpen] = useState(false);
  const [broadcastMessage, setBroadcastMessage] = useState('');
  const [broadcastNumbers, setBroadcastNumbers] = useState('');
  const [sendingBroadcast, setSendingBroadcast] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/admin/whatsapp/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchConversations = async (search = '') => {
    setLoading(true);
    try {
      const response = await api.get('/api/admin/whatsapp/conversations', {
        params: { search, limit: 50 }
      });
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
      // Only show error toast for actual errors, not empty results
      if (error.response?.status !== 200) {
        toast.error('Failed to load conversations');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (phone) => {
    setLoadingMessages(true);
    try {
      const response = await api.get(`/api/admin/whatsapp/conversations/${phone}`);
      setMessages(response.data.messages || []);
      setSelectedConversation({
        phone,
        vendor: response.data.vendor
      });
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      toast.error('Failed to load messages');
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchConversations(searchQuery);
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;
    
    setSending(true);
    try {
      await api.post('/api/admin/whatsapp/send', {
        phone: selectedConversation.phone,
        message: newMessage
      });
      setNewMessage('');
      // Refresh messages
      fetchMessages(selectedConversation.phone);
      toast.success('Message sent!');
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const sendBroadcast = async () => {
    if (!broadcastMessage.trim() || !broadcastNumbers.trim()) {
      toast.error('Please enter message and phone numbers');
      return;
    }
    
    const numbers = broadcastNumbers.split('\n').map(n => n.trim()).filter(n => n);
    if (numbers.length === 0) {
      toast.error('Please enter at least one phone number');
      return;
    }
    
    setSendingBroadcast(true);
    try {
      const response = await api.post('/api/admin/whatsapp/broadcast', {
        phone_numbers: numbers,
        message: broadcastMessage
      });
      toast.success(`Broadcast sent: ${response.data.success_count}/${response.data.total} successful`);
      setBroadcastOpen(false);
      setBroadcastMessage('');
      setBroadcastNumbers('');
      fetchStats();
    } catch (error) {
      console.error('Failed to send broadcast:', error);
      toast.error('Failed to send broadcast');
    } finally {
      setSendingBroadcast(false);
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff/60000)}m ago`;
    if (diff < 86400000) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <DashboardLayout>
      <div className="h-[calc(100vh-120px)] flex flex-col" data-testid="whatsapp-inbox-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">WhatsApp Inbox</h1>
            <p className="text-slate-500">Manage vendor conversations</p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => { fetchStats(); fetchConversations(searchQuery); }}
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button 
              className="bg-green-600 hover:bg-green-700"
              onClick={() => setBroadcastOpen(true)}
              data-testid="broadcast-btn"
            >
              <Megaphone className="w-4 h-4 mr-2" />
              Broadcast
            </Button>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            <Card className="bg-gradient-to-br from-blue-50 to-white">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="text-xs text-slate-500">Total Messages</p>
                    <p className="text-lg font-bold">{stats.total_messages}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-green-50 to-white">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <Inbox className="w-5 h-5 text-green-600" />
                  <div>
                    <p className="text-xs text-slate-500">Incoming</p>
                    <p className="text-lg font-bold">{stats.incoming}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-orange-50 to-white">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <Send className="w-5 h-5 text-orange-600" />
                  <div>
                    <p className="text-xs text-slate-500">Outgoing</p>
                    <p className="text-lg font-bold">{stats.outgoing}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-red-50 to-white">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <div>
                    <p className="text-xs text-slate-500">Unread</p>
                    <p className="text-lg font-bold">{stats.unread}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-purple-50 to-white">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="text-xs text-slate-500">Conversations</p>
                    <p className="text-lg font-bold">{stats.unique_conversations}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content - Conversations and Messages */}
        <div className="flex-1 flex gap-4 overflow-hidden">
          {/* Conversations List */}
          <Card className="w-96 flex flex-col overflow-hidden">
            <CardHeader className="py-3 border-b">
              <form onSubmit={handleSearch} className="flex gap-2">
                <Input 
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1"
                  data-testid="search-input"
                />
                <Button type="submit" size="icon" variant="outline">
                  <Search className="w-4 h-4" />
                </Button>
              </form>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-0">
              {loading ? (
                <div className="flex items-center justify-center h-32">
                  <RefreshCw className="w-6 h-6 animate-spin text-slate-400" />
                </div>
              ) : conversations.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-slate-400">
                  <MessageCircle className="w-8 h-8 mb-2" />
                  <p className="text-sm">No conversations yet</p>
                </div>
              ) : (
                <div className="divide-y">
                  {conversations.map((conv) => (
                    <div
                      key={conv._id}
                      className={`p-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                        selectedConversation?.phone === conv.phone ? 'bg-orange-50 border-l-4 border-orange-500' : ''
                      }`}
                      onClick={() => fetchMessages(conv.phone)}
                      data-testid={`conversation-${conv._id}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center">
                            <User className="w-5 h-5 text-slate-500" />
                          </div>
                          <div>
                            <p className="font-medium text-slate-800 text-sm">
                              {conv.vendor_name || conv.phone}
                            </p>
                            <p className="text-xs text-slate-500">{conv.phone}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-slate-400">{formatTime(conv.last_message_time)}</p>
                          {conv.unread_count > 0 && (
                            <Badge className="bg-green-500 text-white text-xs mt-1">
                              {conv.unread_count}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 mt-1 truncate pl-12">
                        {conv.last_direction === 'outgoing' && <span className="text-slate-400">You: </span>}
                        {conv.last_message}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Messages Panel */}
          <Card className="flex-1 flex flex-col overflow-hidden">
            {selectedConversation ? (
              <>
                {/* Chat Header */}
                <CardHeader className="py-3 border-b bg-white">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="md:hidden"
                        onClick={() => setSelectedConversation(null)}
                      >
                        <ChevronLeft className="w-5 h-5" />
                      </Button>
                      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                        <Phone className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">
                          {selectedConversation.vendor?.company_name || selectedConversation.phone}
                        </p>
                        <p className="text-xs text-slate-500">
                          {selectedConversation.phone}
                          {selectedConversation.vendor && (
                            <span> • {selectedConversation.vendor.city}, {selectedConversation.vendor.state}</span>
                          )}
                        </p>
                      </div>
                    </div>
                    {selectedConversation.vendor && (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => navigate(`/vendor-profile/${selectedConversation.vendor.vendor_id}`)}
                      >
                        View Profile
                      </Button>
                    )}
                  </div>
                </CardHeader>

                {/* Messages */}
                <CardContent className="flex-1 overflow-y-auto p-4 bg-slate-50">
                  {loadingMessages ? (
                    <div className="flex items-center justify-center h-full">
                      <RefreshCw className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400">
                      <MessageCircle className="w-12 h-12 mb-2" />
                      <p>No messages in this conversation</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {messages.map((msg, idx) => (
                        <div
                          key={msg.message_id || idx}
                          className={`flex ${msg.direction === 'outgoing' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-[70%] rounded-lg p-3 ${
                              msg.direction === 'outgoing'
                                ? 'bg-green-600 text-white rounded-br-none'
                                : 'bg-white text-slate-800 rounded-bl-none shadow-sm'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                            <div className={`flex items-center justify-end gap-1 mt-1 ${
                              msg.direction === 'outgoing' ? 'text-green-200' : 'text-slate-400'
                            }`}>
                              <span className="text-xs">{formatTime(msg.created_at)}</span>
                              {msg.direction === 'outgoing' && (
                                msg.read ? <CheckCheck className="w-3 h-3" /> : <Check className="w-3 h-3" />
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </CardContent>

                {/* Message Input */}
                <div className="p-3 border-t bg-white">
                  <div className="flex gap-2">
                    <Textarea
                      placeholder="Type a message..."
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      className="flex-1 min-h-[44px] max-h-32 resize-none"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          sendMessage();
                        }
                      }}
                      data-testid="message-input"
                    />
                    <Button 
                      onClick={sendMessage}
                      disabled={sending || !newMessage.trim()}
                      className="bg-green-600 hover:bg-green-700 self-end"
                      data-testid="send-message-btn"
                    >
                      {sending ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                <MessageSquare className="w-16 h-16 mb-4" />
                <p className="text-lg font-medium">Select a conversation</p>
                <p className="text-sm">Choose a conversation from the list to view messages</p>
              </div>
            )}
          </Card>
        </div>

        {/* Broadcast Dialog */}
        <Dialog open={broadcastOpen} onOpenChange={setBroadcastOpen}>
          <DialogContent className="max-w-lg" data-testid="broadcast-dialog">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Megaphone className="w-5 h-5 text-green-600" />
                Broadcast Message
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Phone Numbers (one per line)
                </label>
                <Textarea
                  placeholder="919876543210&#10;919876543211&#10;919876543212"
                  value={broadcastNumbers}
                  onChange={(e) => setBroadcastNumbers(e.target.value)}
                  rows={4}
                  data-testid="broadcast-numbers-input"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Enter phone numbers with country code, one per line
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Message
                </label>
                <Textarea
                  placeholder="Enter your broadcast message..."
                  value={broadcastMessage}
                  onChange={(e) => setBroadcastMessage(e.target.value)}
                  rows={4}
                  data-testid="broadcast-message-input"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Use *text* for bold, _text_ for italic
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setBroadcastOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={sendBroadcast}
                disabled={sendingBroadcast}
                className="bg-green-600 hover:bg-green-700"
                data-testid="send-broadcast-btn"
              >
                {sendingBroadcast ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Send Broadcast
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}
