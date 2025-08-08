import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { v4 as uuidv4 } from 'uuid';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    PaperAirplaneIcon, 
    CheckCircleIcon,
    ClockIcon 
} from '@heroicons/react/24/outline';
import { Bot, User, Wheat, TrendingUp, CloudRain, Banknote } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import './Chat.css';

const Chat = () => {
    const [messages, setMessages] = useState([
        { 
            id: 'initial', 
            text: 'Hello! I am Agri Sarthi, your agricultural assistant. How can I help you today? Ask me about crop prices, soil health, weather forecasts, or government schemes.', 
            sender: 'bot' 
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [threadId] = useState(uuidv4());
    const [isConnected, setIsConnected] = useState(false);
    const chatWindowRef = useRef(null);

    // Test backend connectivity on component mount
    useEffect(() => {
        const testBackend = async () => {
            console.log('=== FRONTEND DEBUG ===');
            const testUrls = [
                'http://localhost:8000/test',
                'http://127.0.0.1:8000/test'
            ];
            
            for (const url of testUrls) {
                console.log(`Testing backend connectivity to: ${url}`);
                
                try {
                    const response = await fetch(url);
                    console.log(`Response from ${url}:`, response);
                    console.log('Response status:', response.status);
                    console.log('Response ok:', response.ok);
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log(`Backend test successful for ${url}:`, data);
                        setIsConnected(true);
                        toast.success('Connected to AI assistant!');
                        break;
                    } else {
                        console.error(`Backend test failed for ${url} with status:`, response.status);
                    }
                } catch (error) {
                    console.error(`Backend connection test failed for ${url}:`);
                    console.error('Error type:', error.constructor.name);
                    console.error('Error message:', error.message);
                    console.log('This usually means the backend server is not running or not accessible');
                }
            }
            
            if (!isConnected) {
                toast.error('Unable to connect to AI assistant. Please ensure the backend is running.');
            }
            console.log('======================');
        };
        testBackend();
    }, [isConnected]);

    useEffect(() => {
        if (chatWindowRef.current) {
            chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    const handleInputChange = (e) => {
        setInputValue(e.target.value);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!inputValue.trim() || isLoading) return;

        const userMessage = { id: uuidv4(), text: inputValue, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        const originalInput = inputValue;
        setInputValue('');
        setIsLoading(true);

        const botMessageId = uuidv4();
        setMessages(prev => [...prev, { id: botMessageId, text: '', sender: 'bot' }]);

        console.log('Attempting to connect to backend...');
        
        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify({ message: originalInput, thread_id: threadId }),
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                throw new Error('Response body is null');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                const chunk = decoder.decode(value, { stream: true });
                
                const lines = chunk.split('\n\n');
                lines.forEach(line => {
                    if (line.startsWith('data:')) {
                        const dataStr = line.substring(5);
                        try {
                            const data = JSON.parse(dataStr);
                            setMessages(prev => prev.map(msg => {
                                if (msg.id === botMessageId) {
                                    let newText = msg.text;

                                    if (data.content) {
                                        newText += data.content;
                                    }
                                    
                                    return { ...msg, text: newText };
                                }
                                return msg;
                            }));
                        } catch (error) {
                            console.error('Error parsing JSON chunk:', dataStr, error);
                        }
                    }
                });
            }

        } catch (error) {
            console.error('Fetch error:', error);
            toast.error('Failed to get response. Please try again.');
            setMessages(prev => prev.map(msg => 
                msg.id === botMessageId ? { ...msg, text: 'Sorry, I encountered an error. Please try again.' } : msg
            ));
        } finally {
            setIsLoading(false);
        }
    };

    const quickQuestions = [
        { 
            icon: <TrendingUp className="w-4 h-4" />, 
            text: "What is the current price of wheat in Punjab?",
            category: "Market"
        },
        { 
            icon: <Wheat className="w-4 h-4" />, 
            text: "What crops are suitable for Uttar Pradesh soil?",
            category: "Crop Advisory"
        },
        { 
            icon: <CloudRain className="w-4 h-4" />, 
            text: "Are there any weather warnings for Rajasthan?",
            category: "Weather"
        },
        { 
            icon: <Banknote className="w-4 h-4" />, 
            text: "Tell me about PM-KUSUM scheme",
            category: "Schemes"
        }
    ];

    const handleQuickQuestion = (question) => {
        setInputValue(question.text);
    };

    return (
        <div className="chat-page">
            <Toaster position="top-right" />
            <motion.div 
                className="chat-container"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div className="chat-header">
                    <div className="chat-title">
                        <Bot className="chat-icon" size={28} />
                        <div>
                            <h2>AI Agricultural Assistant</h2>
                            <p>Get instant farming advice and insights</p>
                        </div>
                    </div>
                    <div className={`status-indicator ${isConnected ? 'online' : 'offline'}`}>
                        <div className="status-dot"></div>
                        <span>{isConnected ? 'Online' : 'Connecting...'}</span>
                        {isConnected ? <CheckCircleIcon className="w-4 h-4" /> : <ClockIcon className="w-4 h-4" />}
                    </div>
                </div>
                
                <div className="chat-window" ref={chatWindowRef}>
                    <AnimatePresence>
                        {messages.map(msg => (
                            <motion.div 
                                key={msg.id} 
                                className={`message ${msg.sender}`}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.3 }}
                            >
                                <div className="avatar">
                                    {msg.sender === 'bot' ? 
                                        <Bot className="avatar-icon" size={24} /> : 
                                        <User className="avatar-icon" size={24} />
                                    }
                                </div>
                                <div className="message-content">
                                    {msg.text === '' && isLoading ? (
                                        <div className="typing-indicator">
                                            <span></span><span></span><span></span>
                                        </div>
                                    ) : (
                                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>

                {messages.length <= 1 && (
                    <motion.div 
                        className="quick-questions"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                    >
                        <h3>Try asking:</h3>
                        <div className="quick-questions-grid">
                            {quickQuestions.map((question, index) => (
                                <motion.button 
                                    key={index}
                                    className="quick-question-btn"
                                    onClick={() => handleQuickQuestion(question)}
                                    whileHover={{ scale: 1.02, y: -2 }}
                                    whileTap={{ scale: 0.98 }}
                                >
                                    <div className="question-header">
                                        {question.icon}
                                        <span className="question-category">{question.category}</span>
                                    </div>
                                    <p>{question.text}</p>
                                </motion.button>
                            ))}
                        </div>
                    </motion.div>
                )}
                
                <div className="input-area">
                    <form className="input-form" onSubmit={handleSubmit}>
                        <div className="input-wrapper">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={handleInputChange}
                                placeholder="Ask about crops, prices, weather, or schemes..."
                                disabled={isLoading}
                            />
                            <motion.button 
                                type="submit" 
                                disabled={isLoading || !inputValue.trim()}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <PaperAirplaneIcon className="send-icon w-5 h-5" />
                            </motion.button>
                        </div>
                    </form>
                </div>
            </motion.div>
        </div>
    );
};

export default Chat;