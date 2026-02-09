import React from 'react';
import { Wheat, Mail, Phone, Clock } from 'lucide-react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <Wheat className="footer-logo-icon" size={32} />
              <span className="footer-logo-text">Agri Sarthi</span>
            </div>
            <p className="footer-description">
              Empowering farmers with AI-driven insights for better crop management, 
              market decisions, and sustainable farming practices.
            </p>
          </div>
          
          <div className="footer-section">
            <h3 className="footer-title">Services</h3>
            <ul className="footer-links">
              <li>Crop Advisory</li>
              <li>Market Prices</li>
              <li>Weather Alerts</li>
              <li>Soil Analysis</li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h3 className="footer-title">Resources</h3>
            <ul className="footer-links">
              <li>Government Schemes</li>
              <li>Farming Tips</li>
              <li>FAQ</li>
              <li>Support</li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h3 className="footer-title">Contact</h3>
            <div className="contact-info">
              <p><Mail className="contact-icon" size={16} /> help@agrisarthi.com</p>
              <p><Phone className="contact-icon" size={16} /> 1800-AGRI-HELP</p>
              <p><Clock className="contact-icon" size={16} /> 24/7 AI Support Available</p>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>&copy; 2025 Agri Sarthi. All rights reserved. | Made with ❤️ for Indian Farmers</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;