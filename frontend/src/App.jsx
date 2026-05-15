import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Discovery from './pages/Discovery';
import Review from './pages/Review';
import Apply from './pages/Apply';
import Interview from './pages/Interview';

const PageTitle = ({ title }) => (
  <div className="flex flex-col gap-4">
    <h1 className="text-3xl font-bold text-white tracking-tight">{title}</h1>
    <p className="text-zinc-400 font-mono text-sm uppercase tracking-widest">Coming soon...</p>
  </div>
);

const App = () => {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/discover" element={<Discovery />} />
          <Route path="/review" element={<Review />} />
          <Route path="/apply" element={<Apply />} />
          <Route path="/interview/:companyId" element={<Interview />} />
          <Route path="/interview" element={<Interview />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
