import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../App";
import { Bell, Check, Trash2, FileText, DollarSign, Package, MessageSquare, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Button } from "./ui/button";
import { toast } from "sonner";

const NotificationBell = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    fetchNotifications();
    // Poll for new notifications every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await api.get("/notifications?limit=10");
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  };

  const markAsRead = async (notificationId, e) => {
    e?.stopPropagation();
    try {
      await api.put(`/notifications/${notificationId}/read`);
      setNotifications(prev => 
        prev.map(n => n.notification_id === notificationId ? {...n, is_read: true} : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      toast.error("Failed to mark as read");
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.put("/notifications/read-all");
      setNotifications(prev => prev.map(n => ({...n, is_read: true})));
      setUnreadCount(0);
      toast.success("All notifications marked as read");
    } catch (error) {
      toast.error("Failed to mark all as read");
    }
  };

  const deleteNotification = async (notificationId, e) => {
    e?.stopPropagation();
    try {
      await api.delete(`/notifications/${notificationId}`);
      const wasUnread = notifications.find(n => n.notification_id === notificationId && !n.is_read);
      setNotifications(prev => prev.filter(n => n.notification_id !== notificationId));
      if (wasUnread) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
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
    
    setIsOpen(false);
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "rfq_matched":
        return <FileText className="w-4 h-4 text-orange-500" />;
      case "quote_received":
      case "quote_accepted":
        return <DollarSign className="w-4 h-4 text-green-500" />;
      case "order_status_update":
      case "order_created":
        return <Package className="w-4 h-4 text-blue-500" />;
      case "message_received":
        return <MessageSquare className="w-4 h-4 text-purple-500" />;
      case "negotiation_request":
      case "negotiation_response":
        return <DollarSign className="w-4 h-4 text-amber-500" />;
      default:
        return <Bell className="w-4 h-4 text-slate-400" />;
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <button 
          className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg relative"
          data-testid="notification-bell"
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-h-[70vh] overflow-hidden" data-testid="notification-dropdown">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="font-semibold text-slate-900">Notifications</h3>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="text-xs text-orange-600 hover:text-orange-700 font-medium"
            >
              Mark all read
            </button>
          )}
        </div>

        {/* Notifications List */}
        <div className="max-h-[400px] overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-6 text-center">
              <Bell className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">No notifications yet</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.notification_id}
                onClick={() => handleNotificationClick(notification)}
                className={`flex items-start gap-3 px-4 py-3 hover:bg-slate-50 cursor-pointer border-b last:border-b-0 transition-colors ${
                  !notification.is_read ? "bg-orange-50/50" : ""
                }`}
                data-testid={`notification-item-${notification.notification_id}`}
              >
                <div className="mt-0.5">
                  {getNotificationIcon(notification.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${!notification.is_read ? "font-semibold text-slate-900" : "text-slate-700"}`}>
                    {notification.title}
                  </p>
                  <p className="text-xs text-slate-500 truncate">
                    {notification.message}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {formatTime(notification.created_at)}
                  </p>
                </div>
                <div className="flex gap-1">
                  {!notification.is_read && (
                    <button
                      onClick={(e) => markAsRead(notification.notification_id, e)}
                      className="p-1 text-slate-400 hover:text-green-600 rounded"
                      title="Mark as read"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => deleteNotification(notification.notification_id, e)}
                    className="p-1 text-slate-400 hover:text-red-600 rounded"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <div className="p-2">
              <Link to="/notifications">
                <Button 
                  variant="ghost" 
                  className="w-full text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                  onClick={() => setIsOpen(false)}
                >
                  View All Notifications
                </Button>
              </Link>
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NotificationBell;
