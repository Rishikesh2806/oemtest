import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { 
  FolderOpen, 
  File, 
  Image, 
  FileText, 
  Trash2, 
  Download, 
  RefreshCw, 
  Search,
  HardDrive,
  Filter
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function FileManager() {
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchPrefix, setSearchPrefix] = useState('oemlinker');
  const [filter, setFilter] = useState('all'); // all, machines, drawings

  useEffect(() => {
    fetchFiles();
    fetchStats();
  }, []);

  const fetchFiles = async (prefix = searchPrefix) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/admin/files?prefix=${encodeURIComponent(prefix)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setFiles(data.files || []);
      } else {
        toast.error('Failed to fetch files');
      }
    } catch (error) {
      console.error('Error fetching files:', error);
      toast.error('Error loading files');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/admin/files/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const deleteFile = async (path) => {
    if (!window.confirm(`Are you sure you want to delete this file?\n\n${path}`)) {
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/admin/files/${encodeURIComponent(path)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('File deleted successfully');
        fetchFiles();
        fetchStats();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to delete file');
      }
    } catch (error) {
      toast.error('Error deleting file');
    }
  };

  const getFileIcon = (file) => {
    const name = file.name?.toLowerCase() || '';
    const contentType = file.content_type || '';
    
    if (contentType.startsWith('image/') || /\.(jpg|jpeg|png|gif|webp)$/i.test(name)) {
      return <Image className="w-5 h-5 text-green-500" />;
    } else if (contentType === 'application/pdf' || name.endsWith('.pdf')) {
      return <FileText className="w-5 h-5 text-red-500" />;
    } else {
      return <File className="w-5 h-5 text-blue-500" />;
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileCategory = (path) => {
    if (path.includes('/machines/')) return 'machine';
    if (path.includes('/drawings/')) return 'drawing';
    return 'other';
  };

  const filteredFiles = files.filter(file => {
    if (filter === 'all') return true;
    if (filter === 'machines') return file.path?.includes('/machines/');
    if (filter === 'drawings') return file.path?.includes('/drawings/');
    return true;
  });

  const handleSearch = (e) => {
    e.preventDefault();
    fetchFiles(searchPrefix);
  };

  const handleFilterChange = (newFilter) => {
    setFilter(newFilter);
    if (newFilter === 'machines') {
      setSearchPrefix('oemlinker/machines');
      fetchFiles('oemlinker/machines');
    } else if (newFilter === 'drawings') {
      setSearchPrefix('oemlinker/drawings');
      fetchFiles('oemlinker/drawings');
    } else {
      setSearchPrefix('oemlinker');
      fetchFiles('oemlinker');
    }
  };

  return (
    <div className="p-6 space-y-6" data-testid="file-manager-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">File Manager</h1>
          <p className="text-slate-500">Manage cloud storage files</p>
        </div>
        <Button onClick={() => { fetchFiles(); fetchStats(); }} variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <HardDrive className="w-8 h-8 text-blue-500" />
                <div>
                  <p className="text-sm text-slate-500">Total Files</p>
                  <p className="text-2xl font-bold">{stats.total_files}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Image className="w-8 h-8 text-green-500" />
                <div>
                  <p className="text-sm text-slate-500">Machine Images</p>
                  <p className="text-2xl font-bold">{stats.machine_images}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-red-500" />
                <div>
                  <p className="text-sm text-slate-500">Drawings</p>
                  <p className="text-2xl font-bold">{stats.drawings}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <FolderOpen className="w-8 h-8 text-amber-500" />
                <div>
                  <p className="text-sm text-slate-500">Total Size</p>
                  <p className="text-2xl font-bold">{stats.total_size_mb} MB</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search and Filter */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="w-5 h-5" />
            Browse Files
          </CardTitle>
          <CardDescription>Search and manage files in cloud storage</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-4">
            <form onSubmit={handleSearch} className="flex gap-2 flex-1">
              <Input
                placeholder="Search prefix (e.g., oemlinker/machines)"
                value={searchPrefix}
                onChange={(e) => setSearchPrefix(e.target.value)}
                className="flex-1"
              />
              <Button type="submit">
                <Search className="w-4 h-4 mr-2" />
                Search
              </Button>
            </form>
            <div className="flex gap-2">
              <Button 
                variant={filter === 'all' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => handleFilterChange('all')}
              >
                All
              </Button>
              <Button 
                variant={filter === 'machines' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => handleFilterChange('machines')}
              >
                <Image className="w-4 h-4 mr-1" />
                Machines
              </Button>
              <Button 
                variant={filter === 'drawings' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => handleFilterChange('drawings')}
              >
                <FileText className="w-4 h-4 mr-1" />
                Drawings
              </Button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <FolderOpen className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p>No files found</p>
              <p className="text-sm mt-1">Files uploaded via the app will appear here</p>
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">File</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">Category</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">Size</th>
                    <th className="text-right p-3 text-sm font-medium text-slate-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFiles.map((file, index) => (
                    <tr key={file.path || index} className="border-t hover:bg-slate-50">
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          {getFileIcon(file)}
                          <div>
                            <p className="font-medium text-slate-800 truncate max-w-md" title={file.name}>
                              {file.name}
                            </p>
                            <p className="text-xs text-slate-400 truncate max-w-md" title={file.path}>
                              {file.path}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge variant="outline" className={
                          getFileCategory(file.path) === 'machine' 
                            ? 'bg-green-50 text-green-700' 
                            : getFileCategory(file.path) === 'drawing'
                            ? 'bg-red-50 text-red-700'
                            : 'bg-slate-50 text-slate-700'
                        }>
                          {getFileCategory(file.path)}
                        </Badge>
                      </td>
                      <td className="p-3 text-sm text-slate-600">
                        {formatSize(file.size)}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex gap-2 justify-end">
                          <a
                            href={`${API_URL}${file.storage_url}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-2 py-1 text-sm text-blue-600 hover:text-blue-800"
                          >
                            <Download className="w-4 h-4 mr-1" />
                            View
                          </a>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-800 hover:bg-red-50"
                            onClick={() => deleteFile(file.path)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          <p className="text-sm text-slate-500 mt-4">
            Showing {filteredFiles.length} file(s)
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
