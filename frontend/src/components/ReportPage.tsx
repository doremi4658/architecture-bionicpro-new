import React, { useState, useEffect } from 'react';
import { login, logout } from '../services/auth';

const ReportPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [startDate, setStartDate] = useState('2025-01-01');
  const [endDate, setEndDate] = useState('2025-12-31');

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Простой запрос для проверки сессии (можно сделать отдельный эндпоинт /auth/check)
        const response = await fetch('http://localhost:8000/api/reports?start_date=2025-01-01&end_date=2025-01-01', {
          credentials: 'include'
        });
        if (response.status === 401) throw new Error('Unauthorized');
        setAuthenticated(true);
      } catch {
        setAuthenticated(false);
      }
    };
    checkAuth();
  }, []);

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `http://localhost:8000/api/reports?start_date=${startDate}&end_date=${endDate}`;
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to fetch report');
      }
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `report_${startDate}_${endDate}.csv`;
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button onClick={login} className="px-4 py-2 bg-blue-500 text-white rounded">
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>
        <div className="mb-4 flex space-x-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            />
          </div>
        </div>
        <button
          onClick={handleDownload}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Download Report'}
        </button>
        {error && <div className="mt-4 text-red-500">{error}</div>}
        <button onClick={logout} className="mt-4 text-sm text-gray-600 hover:underline">
          Logout
        </button>
      </div>
    </div>
  );
};

export default ReportPage;