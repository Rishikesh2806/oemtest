import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { 
  MessageSquare, ThumbsUp, ThumbsDown, TrendingUp, 
  Users, BarChart3, RefreshCw, Calendar, Filter,
  ChevronDown, ChevronUp, Star
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ChatAnalyticsTab = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [recentQuestions, setRecentQuestions] = useState([]);
  const [feedbackList, setFeedbackList] = useState([]);
  const [showQuestions, setShowQuestions] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const headers = { Authorization: `Bearer ${token}` };

      // Fetch summary
      const summaryRes = await fetch(`${API_URL}/api/chatbot/analytics/summary?days=${days}`, { headers });
      const summaryData = await summaryRes.json();
      setAnalytics(summaryData);

      // Fetch recent questions
      const questionsRes = await fetch(`${API_URL}/api/chatbot/analytics/questions?days=${days}&limit=20`, { headers });
      const questionsData = await questionsRes.json();
      setRecentQuestions(questionsData.questions || []);

      // Fetch feedback
      const feedbackRes = await fetch(`${API_URL}/api/chatbot/analytics/feedback?days=${days}&limit=20`, { headers });
      const feedbackData = await feedbackRes.json();
      setFeedbackList(feedbackData.feedbacks || []);

    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const getCategoryColor = (category) => {
    const colors = {
      platform_faq: "bg-blue-100 text-blue-700",
      manufacturing: "bg-green-100 text-green-700",
      rfq_help: "bg-purple-100 text-purple-700",
      vendor_matching: "bg-orange-100 text-orange-700",
      order_process: "bg-cyan-100 text-cyan-700",
      support: "bg-red-100 text-red-700",
      general: "bg-slate-100 text-slate-700"
    };
    return colors[category] || colors.general;
  };

  const getCategoryLabel = (category) => {
    const labels = {
      platform_faq: "Platform FAQ",
      manufacturing: "Manufacturing",
      rfq_help: "RFQ Help",
      vendor_matching: "Vendor Matching",
      order_process: "Order Process",
      support: "Support",
      general: "General"
    };
    return labels[category] || category;
  };

  if (loading && !analytics) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Chatbot Analytics</h2>
          <p className="text-sm text-slate-500">Track OEMBot performance and user engagement</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={days.toString()} onValueChange={(v) => setDays(parseInt(v))}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={fetchAnalytics} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Total Conversations</p>
                <p className="text-2xl font-bold text-slate-900">{analytics?.total_conversations || 0}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <MessageSquare className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              {analytics?.unique_sessions || 0} unique sessions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Avg Rating</p>
                <p className="text-2xl font-bold text-slate-900">
                  {analytics?.feedback?.average_rating?.toFixed(1) || "N/A"}
                  <span className="text-sm font-normal text-slate-400">/5</span>
                </p>
              </div>
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <Star className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              {analytics?.feedback?.total_feedback || 0} ratings received
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Satisfaction Rate</p>
                <p className="text-2xl font-bold text-green-600">
                  {analytics?.feedback?.satisfaction_rate?.toFixed(0) || 0}%
                </p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <ThumbsUp className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs">
              <span className="text-green-600">👍 {analytics?.feedback?.positive || 0}</span>
              <span className="text-red-600">👎 {analytics?.feedback?.negative || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Avg Messages/Session</p>
                <p className="text-2xl font-bold text-slate-900">
                  {analytics?.avg_messages_per_session?.toFixed(1) || 0}
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Avg response: {analytics?.avg_response_length || 0} chars
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Categories & Keywords */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Question Categories */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Question Categories
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics?.categories && Object.entries(analytics.categories)
                .sort(([,a], [,b]) => b - a)
                .map(([category, count]) => {
                  const total = analytics.total_conversations || 1;
                  const percentage = ((count / total) * 100).toFixed(0);
                  return (
                    <div key={category} className="flex items-center gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(category)}`}>
                        {getCategoryLabel(category)}
                      </span>
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-orange-500 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-slate-600 w-16 text-right">{count} ({percentage}%)</span>
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>

        {/* Top Keywords */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Filter className="w-4 h-4" />
              Top Keywords
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {analytics?.top_keywords?.slice(0, 15).map(([keyword, count], idx) => (
                <span 
                  key={keyword}
                  className={`px-3 py-1 rounded-full text-sm ${
                    idx < 3 ? 'bg-orange-100 text-orange-700 font-medium' : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {keyword} <span className="text-xs opacity-60">({count})</span>
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Questions */}
      <Card>
        <CardHeader 
          className="cursor-pointer hover:bg-slate-50 transition-colors"
          onClick={() => setShowQuestions(!showQuestions)}
        >
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Recent Questions ({recentQuestions.length})
            </CardTitle>
            {showQuestions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </CardHeader>
        {showQuestions && (
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {recentQuestions.map((q) => (
                <div key={q.chat_id} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm text-slate-700 font-medium">{q.user_message}</p>
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{q.bot_response?.substring(0, 150)}...</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`px-2 py-0.5 rounded text-xs ${getCategoryColor(q.category)}`}>
                        {getCategoryLabel(q.category)}
                      </span>
                      {q.feedback && (
                        <span className={`text-xs ${q.feedback.rating >= 4 ? 'text-green-600' : 'text-red-600'}`}>
                          {q.feedback.rating >= 4 ? '👍' : '👎'}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    {new Date(q.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Recent Feedback */}
      <Card>
        <CardHeader 
          className="cursor-pointer hover:bg-slate-50 transition-colors"
          onClick={() => setShowFeedback(!showFeedback)}
        >
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <ThumbsUp className="w-4 h-4" />
              Recent Feedback ({feedbackList.length})
            </CardTitle>
            {showFeedback ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </CardHeader>
        {showFeedback && (
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {feedbackList.map((f) => (
                <div key={f.chat_id} className={`p-3 rounded-lg border ${
                  f.feedback?.rating >= 4 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-lg ${f.feedback?.rating >= 4 ? '' : ''}`}>
                          {f.feedback?.rating >= 4 ? '👍' : '👎'}
                        </span>
                        <span className="text-xs text-slate-500">
                          {new Date(f.feedback?.submitted_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-slate-700"><strong>Q:</strong> {f.user_message}</p>
                      <p className="text-xs text-slate-500 mt-1"><strong>A:</strong> {f.bot_response?.substring(0, 200)}...</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
};

export default ChatAnalyticsTab;
