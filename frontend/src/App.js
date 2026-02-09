import React, { useState } from 'react';
import './App.css';
import './index.css';
import HomePage from './components/HomePage';
import Chat from './components/Chat';
import Header from './components/Header';
import Footer from './components/Footer';

function App() {
  const [currentPage, setCurrentPage] = useState('home');

  const renderPage = () => {
    switch(currentPage) {
      case 'chat':
        return <Chat />;
      case 'home':
      default:
        return <HomePage onNavigateToChat={() => setCurrentPage('chat')} />;
    }
  };

  return (
    <div className="App">
      <Header currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <main className="main-content">
        {renderPage()}
      </main>
      <Footer />
    </div>
  );
}

export default App;