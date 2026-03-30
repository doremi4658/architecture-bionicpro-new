import React, { useState, useEffect } from 'react';
import { login, logout, downloadReport } from '../services/auth';

const ReportPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await downloadReport();
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
      const blob = await downloadReport();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'report.txt';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>
        <button
          onClick={handleDownload}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Download Report'}
        </button>
        {error && <div className="mt-4 text-red-500">{error}</div>}
        <button onClick={() => logout()} className="mt-4 text-sm text-gray-600 hover:underline">
          Logout
        </button>
      </div>
    </div>
  );
};

export default ReportPage;