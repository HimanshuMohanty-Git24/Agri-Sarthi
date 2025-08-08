import React from 'react';
import { motion } from 'framer-motion';
import { 
  Sprout, 
  TrendingUp, 
  Building2, 
  CloudSun, 
  Microscope, 
  BarChart3,
  ArrowRight,
  CheckCircle,
  Users,
  MapPin,
  Clock,
  Target
} from 'lucide-react';
import './HomePage.css';

const HomePage = ({ onNavigateToChat }) => {
  const features = [
    {
      icon: <Sprout className="feature-icon-svg" />,
      title: 'Crop Advisory',
      description: 'Get personalized recommendations for crops suitable for your soil and climate conditions.'
    },
    {
      icon: <TrendingUp className="feature-icon-svg" />,
      title: 'Market Prices',
      description: 'Real-time mandi rates and price trends to help you make informed selling decisions.'
    },
    {
      icon: <Building2 className="feature-icon-svg" />,
      title: 'Government Schemes',
      description: 'Information about subsidies, loans, and government programs for farmers.'
    },
    {
      icon: <CloudSun className="feature-icon-svg" />,
      title: 'Weather & Alerts',
      description: 'Weather forecasts and disaster warnings to protect your crops.'
    },
    {
      icon: <Microscope className="feature-icon-svg" />,
      title: 'Soil Analysis',
      description: 'Detailed soil health reports and fertilizer recommendations.'
    },
    {
      icon: <BarChart3 className="feature-icon-svg" />,
      title: 'Analytics',
      description: 'Data-driven insights to optimize your farming operations.'
    }
  ];

  const stats = [
    { icon: <Users />, number: '10K+', label: 'Farmers Helped' },
    { icon: <MapPin />, number: '500+', label: 'Districts Covered' },
    { icon: <Clock />, number: '24/7', label: 'AI Support' },
    { icon: <Target />, number: '95%', label: 'Accuracy Rate' }
  ];

  return (
    <div className="homepage">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <motion.div 
            className="hero-text"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="hero-title">
              Empowering Farmers with <span className="highlight">AI Technology</span>
            </h1>
            <p className="hero-description">
              Get instant advice on crops, soil health, market prices, and government schemes. 
              Make smarter farming decisions with our AI-powered agricultural assistant.
            </p>
            <div className="hero-actions">
              <motion.button 
                className="cta-primary" 
                onClick={onNavigateToChat}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Start Farming Consultation
                <ArrowRight className="w-5 h-5" />
              </motion.button>
              <motion.button 
                className="cta-secondary"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Learn More
              </motion.button>
            </div>
          </motion.div>
          <motion.div 
            className="hero-image"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className="farmer-illustration">
              🚜
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <div className="container">
          <motion.h2 
            className="section-title"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
          >
            How Agri Sarthi Helps You
          </motion.h2>
          <div className="features-grid">
            {features.map((feature, index) => (
              <motion.div 
                key={index} 
                className="feature-card"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
              >
                <div className="feature-icon">{feature.icon}</div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">{feature.description}</p>
                <CheckCircle className="feature-check" size={20} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats">
        <div className="container">
          <div className="stats-grid">
            {stats.map((stat, index) => (
              <motion.div 
                key={index}
                className="stat-item"
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <div className="stat-icon">{stat.icon}</div>
                <div className="stat-number">{stat.number}</div>
                <div className="stat-label">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="container">
          <motion.div 
            className="cta-content"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2>Ready to Transform Your Farming?</h2>
            <p>Join thousands of farmers who are already using AI to improve their yields and profits.</p>
            <motion.button 
              className="cta-large" 
              onClick={onNavigateToChat}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Get Started Now
              <ArrowRight className="w-6 h-6" />
            </motion.button>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;