import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { 
  Users, Building2, FileText, BarChart3, MessageSquare, Shield, 
  FolderOpen, AlertTriangle, DollarSign, TrendingUp, Package,
  Wrench, Send, Plus, Search, CheckCircle, ShoppingCart, Truck,
  Sparkles
} from 'lucide-react';
import { usePermittedActions } from '../hooks/usePermissions';

// Icon mapping
const IconMap = {
  Users,
  Building2,
  FileText,
  BarChart3,
  MessageSquare,
  Shield,
  FolderOpen,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  Package,
  Wrench,
  Send,
  Plus,
  Search,
  CheckCircle,
  ShoppingCart,
  Truck,
  Sparkles
};

// Color mapping for cards
const colorClasses = {
  blue: 'bg-blue-500/10 text-blue-600 border-blue-200 hover:bg-blue-500/20',
  green: 'bg-green-500/10 text-green-600 border-green-200 hover:bg-green-500/20',
  purple: 'bg-purple-500/10 text-purple-600 border-purple-200 hover:bg-purple-500/20',
  orange: 'bg-orange-500/10 text-orange-600 border-orange-200 hover:bg-orange-500/20',
  red: 'bg-red-500/10 text-red-600 border-red-200 hover:bg-red-500/20',
  yellow: 'bg-yellow-500/10 text-yellow-600 border-yellow-200 hover:bg-yellow-500/20',
  teal: 'bg-teal-500/10 text-teal-600 border-teal-200 hover:bg-teal-500/20',
  gray: 'bg-gray-500/10 text-gray-600 border-gray-200 hover:bg-gray-500/20',
};

const iconBgClasses = {
  blue: 'bg-blue-500/20 text-blue-600',
  green: 'bg-green-500/20 text-green-600',
  purple: 'bg-purple-500/20 text-purple-600',
  orange: 'bg-orange-500/20 text-orange-600',
  red: 'bg-red-500/20 text-red-600',
  yellow: 'bg-yellow-500/20 text-yellow-600',
  teal: 'bg-teal-500/20 text-teal-600',
  gray: 'bg-gray-500/20 text-gray-600',
};

// Single action card
function ActionCard({ action }) {
  const Icon = IconMap[action.icon] || FileText;
  const cardColor = colorClasses[action.color] || colorClasses.gray;
  const iconBg = iconBgClasses[action.color] || iconBgClasses.gray;

  return (
    <Link to={action.path} data-testid={`action-card-${action.id}`}>
      <Card className={`h-full transition-all duration-200 cursor-pointer border ${cardColor}`}>
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg ${iconBg}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm">{action.title}</h3>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {action.description}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

// Permitted Actions Grid Component
export default function PermittedActions({ 
  dashboardType, 
  title = "Quick Actions",
  description = "Actions available to you based on your permissions",
  columns = 4,
  showEmpty = true 
}) {
  const { actions, loading } = usePermittedActions(dashboardType);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-muted/50 rounded-lg animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (actions.length === 0 && !showEmpty) {
    return null;
  }

  const gridCols = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
  };

  return (
    <Card data-testid="permitted-actions-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {title}
              <Badge variant="secondary" className="ml-2">
                {actions.length} available
              </Badge>
            </CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {actions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No actions available</p>
            <p className="text-sm">Contact admin for additional permissions</p>
          </div>
        ) : (
          <div className={`grid ${gridCols[columns] || gridCols[4]} gap-4`}>
            {actions.map(action => (
              <ActionCard key={action.id} action={action} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Export individual components for custom layouts
export { ActionCard };
