import React, { useState } from 'react';
import { 
  ClipboardIcon, 
  SpeakerWaveIcon, 
  LanguageIcon,
  CheckIcon,
  StopIcon
} from '@heroicons/react/24/outline';
import sarvamService, { SUPPORTED_LANGUAGES } from '../services/sarvamService';
import './MessageActions.css';

const MessageActions = ({ message, isBot }) => {
  const [copied, setCopied] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedText, setTranslatedText] = useState('');
  const [translatedLanguage, setTranslatedLanguage] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [showLanguageSelector, setShowLanguageSelector] = useState(false);
  const [audioCache, setAudioCache] = useState({});
  const [currentAudio, setCurrentAudio] = useState(null);

  // Copy to clipboard
  const handleCopy = async () => {
    try {
      const textToCopy = translatedText || message.text;
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy text:', error);
    }
  };

  // Translate text
  const handleTranslate = async (targetLanguage) => {
    if (isTranslating) return;
    
    setIsTranslating(true);
    setShowLanguageSelector(false);

    try {
      const result = await sarvamService.translateText(
        message.text,
        targetLanguage,
        'auto'
      );
      
      setTranslatedText(result.translatedText);
      setTranslatedLanguage(targetLanguage);
    } catch (error) {
      console.error('Translation failed:', error);
      alert('Translation failed. Please try again.');
    } finally {
      setIsTranslating(false);
    }
  };

  // Text to speech
  const handleTTS = async () => {
    if (isPlaying && currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      setCurrentAudio(null);
      setIsPlaying(false);
      return;
    }

    setIsPlaying(true);
    
    try {
      const textToSpeak = translatedText || message.text;
      const languageCode = translatedLanguage || 'en-IN';
      
      // Check cache first
      const cacheKey = `${textToSpeak}_${languageCode}`;
      let audioBase64 = audioCache[cacheKey];
      
      if (!audioBase64) {
        const result = await sarvamService.textToSpeech(textToSpeak, languageCode);
        audioBase64 = result.audioBase64;
        
        // Cache the audio
        setAudioCache(prev => ({
          ...prev,
          [cacheKey]: audioBase64
        }));
      }
      
      const audio = await sarvamService.playAudio(audioBase64);
      setCurrentAudio(audio);

      audio.onended = () => {
        setIsPlaying(false);
        setCurrentAudio(null);
      };

    } catch (error) {
      console.error('TTS failed:', error);
      alert('Text-to-speech failed. Please try again.');
      setIsPlaying(false);
    }
  };

  // Reset translation
  const handleResetTranslation = () => {
    setTranslatedText('');
    setTranslatedLanguage('');
  };

  if (!isBot) return null; // Only show actions for bot messages

  return (
    <div className="message-actions">
      <div className="action-buttons">
        {/* Copy Button */}
        <button
          className={`action-btn copy-btn ${copied ? 'copied' : ''}`}
          onClick={handleCopy}
          title="Copy to clipboard"
        >
          {copied ? (
            <CheckIcon className="action-icon" />
          ) : (
            <ClipboardIcon className="action-icon" />
          )}
        </button>

        {/* Translate Button */}
        <div className="translate-container">
          <button
            className={`action-btn translate-btn ${isTranslating ? 'loading' : ''}`}
            onClick={() => setShowLanguageSelector(!showLanguageSelector)}
            title="Translate"
            disabled={isTranslating}
          >
            <LanguageIcon className="action-icon" />
          </button>

          {showLanguageSelector && (
            <div className="language-selector">
              <div className="language-grid">
                {Object.entries(SUPPORTED_LANGUAGES).map(([code, name]) => (
                  <button
                    key={code}
                    className="language-option"
                    onClick={() => handleTranslate(code)}
                    disabled={isTranslating}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Text-to-Speech Button */}
        <button
          className={`action-btn tts-btn ${isPlaying ? 'playing' : ''}`}
          onClick={handleTTS}
          title={isPlaying ? "Stop audio" : "Play audio"}
          disabled={isTranslating} // Keep enabled during playback to allow stopping
        >
          {isPlaying ? (
            <StopIcon className="action-icon" />
          ) : (
            <SpeakerWaveIcon className="action-icon" />
          )}
        </button>
      </div>

      {/* Show translated text */}
      {translatedText && (
        <div className="translated-content">
          <div className="translation-header">
            <span className="translation-label">
              Translated to {SUPPORTED_LANGUAGES[translatedLanguage]}:
            </span>
            <button 
              className="reset-translation"
              onClick={handleResetTranslation}
              title="Show original"
            >
              Show Original
            </button>
          </div>
          <div className="translated-text">
            {translatedText}
          </div>
        </div>
      )}

      {/* Loading states */}
      {isTranslating && (
        <div className="action-status">
          <div className="loading-spinner"></div>
          Translating...
        </div>
      )}
      
      {isPlaying && (
        <div className="action-status">
          <div className="audio-animation"></div>
          Playing audio...
        </div>
      )}
    </div>
  );
};

export default MessageActions;