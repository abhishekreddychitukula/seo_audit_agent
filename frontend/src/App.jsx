import React, { useState } from 'react';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import ConsolePage from './pages/ConsolePage';

export default function App() {
  const [activePage, setActivePage] = useState('landing');

  return (
    <div className="app-root">
      <Navbar
        activePage={activePage}
        setActivePage={setActivePage}
      />

      {activePage === 'landing' ? (
        <LandingPage onLaunchConsole={() => setActivePage('console')} />
      ) : (
        <ConsolePage />
      )}
    </div>
  );
}
