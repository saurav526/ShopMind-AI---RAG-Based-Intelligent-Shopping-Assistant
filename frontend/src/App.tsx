import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { LandingPage } from './pages/LandingPage';
import { AssistantPage } from './pages/AssistantPage';
import { ExplorerPage } from './pages/ExplorerPage';
import { ComparisonPage } from './pages/ComparisonPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { SecurityPage } from './pages/SecurityPage';
import { AdminPage } from './pages/AdminPage';
import { authService } from './services/api';
import { User } from './types';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(() => authService.getStoredUser());
  const [compareList, setCompareList] = useState<string[]>(['PROD-LAP-001', 'PROD-LAP-002']);

  const handleToggleCompare = (productId: string) => {
    setCompareList((prev) => {
      if (prev.includes(productId)) {
        return prev.filter((id) => id !== productId);
      }
      if (prev.length >= 4) {
        return [...prev.slice(1), productId];
      }
      return [...prev, productId];
    });
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#070B14] text-slate-100">
        <Navbar user={user} setUser={setUser} compareList={compareList} />
        <main className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route
              path="/assistant"
              element={
                <AssistantPage
                  compareList={compareList}
                  onToggleCompare={handleToggleCompare}
                />
              }
            />
            <Route
              path="/explorer"
              element={
                <ExplorerPage
                  compareList={compareList}
                  onToggleCompare={handleToggleCompare}
                />
              }
            />
            <Route
              path="/compare"
              element={
                <ComparisonPage
                  compareList={compareList}
                  setCompareList={setCompareList}
                />
              }
            />
            <Route path="/evaluation" element={<EvaluationPage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/admin" element={<AdminPage user={user} setUser={setUser} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
