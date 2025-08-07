import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { v4 as uuidv4 } from 'uuid';

const Chat = () => {
    const [messages, setMessages] = useState([
        { id: 'initial', text: 'Hello! I am Agri Sarthi, your agricultural assistant. How can I help you today? Ask me about crop prices, soil health, or government schemes.', sender: 'bot' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [threadId] = useState(uuidv4()); // Unique ID for the conversation session
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
                        break; // Exit loop on first successful connection
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
            console.log('======================');
        };
        testBackend();
    }, []);

    // Effect to scroll to the bottom of the chat window when new messages are added
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

        // Add a placeholder for the bot's response
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
                
                // Process Server-Sent Events
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
                                        // SIMPLIFIED: Just append the content directly without any filtering
                                        // The backend already handles the cleaning, so we trust it
                                        newText += data.content;
                                    }
                                    
                                    // Remove tool events from UI - keep it clean and professional
                                    // Tool events are handled but not shown to user
                                    
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
            setMessages(prev => prev.map(msg => 
                msg.id === botMessageId ? { ...msg, text: 'Sorry, I encountered an error. Please try again.' } : msg
            ));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="app-container">
            <header>
                <h1>🌾 Agri Sarthi</h1>
                <p>Your AI-Powered Farming Advisor</p>
            </header>
            <div className="chat-window" ref={chatWindowRef}>
                {messages.map(msg => (
                    <div key={msg.id} className={`message ${msg.sender}`}>
                        <div className="avatar">{msg.sender === 'bot' ? 'A' : 'Y'}</div>
                        <div className="message-content">
                            <ReactMarkdown>{msg.text}</ReactMarkdown>
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="message bot">
                        <div className="avatar">A</div>
                        <div className="message-content">
                            <div className="typing-indicator">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
            <div className="input-area">
                <form className="input-form" onSubmit={handleSubmit}>
                    <input
                        type="text"
                        value={inputValue}
                        onChange={handleInputChange}
                        placeholder="Ask about crops, prices, or schemes..."
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={isLoading}>
                        Send
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Chat;