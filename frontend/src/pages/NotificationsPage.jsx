import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import {
  Bell, Check, CheckCheck, Trash2, FileText, DollarSign,
  Package, MessageSquare, Loader2, Filter, RefreshCw
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

const NotificationsPage = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // all, unread
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchNotifications();
  }, [filter]);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (filter === "unread") {
        params.append("unread_only", "true");
      }
      const response = await api.get(`/notifications?${params.toString()}`);
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      toast.error("Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await api.put(`/notifications/${notificationId}/read`);
      setNotifications(prev =>
        prev.map(n => n.notification_id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      toast.error("Failed to mark as read");
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.put("/notifications/read-all");
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast.success("All notifications marked as read");
    } catch (error) {
      toast.error("Failed to mark all as read");
    }
  };

  const deleteNotification = async (notificationId) => {
    try {
      await api.delete(`/notifications/${notificationId}`);
      const wasUnread = notifications.find(n => n.notification_id === notificationId && !n.is_read);
      setNotifications(prev => prev.filter(n => n.notification_id !== notificationId));
      if (wasUnread) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
      toast.success("Notification deleted");
    } catch (error) {
      toast.error("Failed to delete notification");
    }
  };

  const handleNotificationClick = (notification) => {
    // Mark as read
    if (!notification.is_read) {
      markAsRead(notification.notification_id);
    }

    // Navigate based on notification type
    const data = notification.data || {};
    switch (notification.type) {
      case "rfq_matched":
        if (data.rfq_id) navigate(`/vendor/rfq/${data.rfq_id}`);
        break;
      case "quote_received":
        if (data.rfq_id) navigate(`/buyer/rfq/${data.rfq_id}`);
        break;
      case "quote_accepted":
        if (data.order_id) navigate(`/orders/${data.order_id}`);
        break;
      case "order_status_update":
        if (data.order_id) navigate(`/orders/${data.order_id}`);
        break;
      case "message_received":
        if (data.conversation_id) navigate(`/chat/${data.conversation_id}`);
        else navigate("/chat");
        break;
      case "negotiation_request":
        // Vendor receives this - navigate to the RFQ where they can respond
        if (data.rfq_id) navigate(`/vendor/rfq/${data.rfq_id}`);
        break;
      case "negotiation_response":
        // Buyer receives this - navigate to the RFQ to see the response
        if (data.rfq_id) navigate(`/buyer/rfq/${data.rfq_id}`);
        break;
      default:
        break;
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "rfq_matched":
        return <FileText className="w-5 h-5 text-orange-500" />;
      case "quote_received":
      case "quote_accepted":
        return <DollarSign className="w-5 h-5 text-green-500" />;
      case "order_status_update":
      case "order_created":
        return <Package className="w-5 h-5 text-blue-500" />;
      case "message_received":
        return <MessageSquare className="w-5 h-5 text-purple-500" />;
      case "negotiation_request":
      case "negotiation_response":
        return <DollarSign className="w-5 h-5 text-amber-500" />;
      default:
        return <Bell className="w-5 h-5 text-slate-400" />;
    }
  };

  const getTypeLabel = (type) => {
    const labels = {
      rfq_matched: "RFQ Match",
      quote_received: "Quote Received",
      quote_accepted: "Quote Accepted",
      order_status_update: "Order Update",
      order_created: "New Order",
      message_received: "New Message",
      negotiation_request: "Negotiation Request",
      negotiation_response: "Negotiation Response",
    };
    return labels[type] || "Notification";
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
    });
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
      <div className="space-y-6" data-testid="notifications-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">Notifications</h1>
            <p className="text-slate-500">
              {unreadCount > 0 ? `You have ${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}` : "All caught up!"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchNotifications}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
            {unreadCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={markAllAsRead}
                className="gap-2"
              >
                <CheckCheck className="w-4 h-4" />
                Mark All Read
              </Button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="unread">Unread Only</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <p className="text-sm text-slate-500">
            {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Notifications List */}
        <Card>
          <CardContent className="p-0">
            {notifications.length === 0 ? (
              <div className="p-12 text-center">
                <Bell className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">
                  {filter === "unread" ? "No unread notifications" : "No notifications yet"}
                </h3>
                <p className="text-slate-500">
                  {filter === "unread"
                    ? "You're all caught up! Check back later."
                    : "When you receive notifications, they'll appear here."}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {notifications.map((notification) => (
                  <div
                    key={notification.notification_id}
                    className={`flex items-start gap-4 p-4 hover:bg-slate-50 cursor-pointer transition-colors ${
                      !notification.is_read ? "bg-orange-50/50" : ""
                    }`}
                    onClick={() => handleNotificationClick(notification)}
                    data-testid={`notification-${notification.notification_id}`}
                  >
                    {/* Icon */}
                    <div className={`mt-1 p-2 rounded-lg ${
                      !notification.is_read ? "bg-orange-100" : "bg-slate-100"
                    }`}>
                      {getNotificationIcon(notification.type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          notification.type === "rfq_matched" ? "bg-orange-100 text-orange-700" :
                          notification.type?.includes("quote") ? "bg-green-100 text-green-700" :
                          notification.type?.includes("order") ? "bg-blue-100 text-blue-700" :
                          notification.type === "message_received" ? "bg-purple-100 text-purple-700" :
                          "bg-slate-100 text-slate-700"
                        }`}>
                          {getTypeLabel(notification.type)}
                        </span>
                        {!notification.is_read && (
                          <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                        )}
                      </div>
                      <h4 className={`text-sm ${!notification.is_read ? "font-semibold text-slate-900" : "font-medium text-slate-700"}`}>
                        {notification.title}
                      </h4>
                      <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="text-xs text-slate-400 mt-2">
                        {formatTime(notification.created_at)}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {!notification.is_read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            markAsRead(notification.notification_id);
                          }}
                          title="Mark as read"
                          className="h-8 w-8 p-0 text-slate-400 hover:text-green-600"
                        >
                          <Check className="w-4 h-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteNotification(notification.notification_id);
                        }}
                        title="Delete"
                        className="h-8 w-8 p-0 text-slate-400 hover:text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default NotificationsPage;
