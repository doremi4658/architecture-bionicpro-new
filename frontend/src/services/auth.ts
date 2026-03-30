export const login = () => {
  window.location.href = 'http://localhost:8000/auth/login';
};

export const logout = async () => {
  await fetch('http://localhost:8000/auth/logout', { method: 'POST', credentials: 'include' });
  window.location.href = '/';
};

export const downloadReport = async (startDate: string, endDate: string): Promise<Blob> => {
  const response = await fetch(`http://localhost:8000/api/reports?start_date=${startDate}&end_date=${endDate}`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Unauthorized');
  return response.blob();
};