export const login = () => {
  window.location.href = 'http://localhost:8000/auth/login';
};

export const logout = async () => {
  await fetch('http://localhost:8000/auth/logout', { method: 'POST', credentials: 'include' });
  window.location.href = '/';
};

export const downloadReport = async (): Promise<Blob> => {
  const response = await fetch('http://localhost:8000/api/reports', {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Unauthorized');
  return response.blob();
};