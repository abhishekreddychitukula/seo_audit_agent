import React, { useState } from 'react';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import ConsolePage from './pages/ConsolePage';

export default function App() {
  const [activePage, setActivePage] = useState('landing');
  const [selectedModel, setSelectedModel] = useState('auto');

  return (
    <div className="app-root">
      <Navbar
        activePage={activePage}
        setActivePage={setActivePage}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
      />

      {activePage === 'landing' ? (
        <LandingPage onLaunchConsole={() => setActivePage('console')} />
      ) : (
        <ConsolePage selectedModel={selectedModel} />
      )}
    </div>
  );
}
