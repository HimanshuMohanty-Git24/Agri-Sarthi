import React from 'react';
import { HomeIcon, ChatBubbleLeftEllipsisIcon } from '@heroicons/react/24/outline';
import { TractorIcon } from 'lucide-react';
import './Header.css';

const Header = ({ currentPage, setCurrentPage }) => {
  return (
    <header className="header">
      <div className="header-container">
        <div className="logo-section">
          <div className="logo">
            <TractorIcon className="logo-icon" size={32} />
            <span className="logo-text">Agri Sarthi</span>
          </div>
          <span className="tagline">Your Smart Farming Companion</span>
        </div>
        
        <nav className="navigation">
          <button 
            className={`nav-btn ${currentPage === 'home' ? 'active' : ''}`}
            onClick={() => setCurrentPage('home')}
          >
            <HomeIcon className="nav-icon" />
            Home
          </button>
          <button 
            className={`nav-btn ${currentPage === 'chat' ? 'active' : ''}`}
            onClick={() => setCurrentPage('chat')}
          >
            <ChatBubbleLeftEllipsisIcon className="nav-icon" />
            AI Assistant
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Header;