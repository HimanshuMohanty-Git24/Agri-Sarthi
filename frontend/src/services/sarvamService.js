// Sarvam API Service — proxied through gateway to avoid CORS
const GATEWAY_BASE = 'http://localhost:8000';

// Available languages for Sarvam API
export const SUPPORTED_LANGUAGES = {
  'en-IN': 'English',
  'hi-IN': 'Hindi',
  'bn-IN': 'Bengali',
  'gu-IN': 'Gujarati',
  'kn-IN': 'Kannada',
  'ml-IN': 'Malayalam',
  'mr-IN': 'Marathi',
  'od-IN': 'Odia',
  'pa-IN': 'Punjabi',
  'ta-IN': 'Tamil',
  'te-IN': 'Telugu',
  'as-IN': 'Assamese',
  'brx-IN': 'Bodo',
  'doi-IN': 'Dogri',
  'kok-IN': 'Konkani',
  'ks-IN': 'Kashmiri',
  'mai-IN': 'Maithili',
  'mni-IN': 'Manipuri',
  'ne-IN': 'Nepali',
  'sa-IN': 'Sanskrit',
  'sat-IN': 'Santali',
  'sd-IN': 'Sindhi',
  'ur-IN': 'Urdu'
};

class SarvamService {
  constructor() {
    this.apiKey = process.env.REACT_APP_SARVAM_API_KEY;
    if (!this.apiKey) {
      console.warn('Sarvam API key not found. Translation and TTS features will not work.');
    }
  }

  async translateText(text, targetLanguage, sourceLanguage = 'en-IN') {
    try {
      const response = await fetch(`${GATEWAY_BASE}/api/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          input: text,
          source_language_code: sourceLanguage === 'auto' ? 'en-IN' : sourceLanguage,
          target_language_code: targetLanguage,
          model: 'mayura:v1',
          enable_preprocessing: true
        })
      });

      if (!response.ok) {
        const errorBody = await response.text();
        console.error('Translation API Error:', errorBody);
        throw new Error(`Translation failed: ${response.status}`);
      }

      const data = await response.json();
      return {
        translatedText: data.translated_text,
        sourceLanguage: data.source_language_code,
        requestId: data.request_id
      };
    } catch (error) {
      console.error('Translation error:', error);
      throw error;
    }
  }

  async textToSpeech(text, targetLanguageCode, speaker = 'anushka') {
    try {
      const response = await fetch(`${GATEWAY_BASE}/api/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: text,
          target_language_code: targetLanguageCode,
          speaker: speaker.toLowerCase(),
          pitch: 0,
          pace: 1,
          loudness: 1,
          speech_sample_rate: 22050,
          enable_preprocessing: true,
          model: 'bulbul:v2'
        })
      });

      if (!response.ok) {
        const errorBody = await response.text();
        console.error('TTS API Error:', errorBody);
        throw new Error(`TTS failed: ${response.status}`);
      }

      const data = await response.json();
      return {
        audioBase64: data.audios[0],
        requestId: data.request_id
      };
    } catch (error) {
      console.error('TTS error:', error);
      throw error;
    }
  }

  // Utility to convert base64 to audio blob
  base64ToAudioBlob(base64String) {
    const byteCharacters = atob(base64String);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: 'audio/wav' });
  }

  // Play audio from base64
  async playAudio(base64String) {
    try {
      const audioBlob = this.base64ToAudioBlob(base64String);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      return new Promise((resolve, reject) => {
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
        };
        audio.onerror = reject;
        audio.play()
          .then(() => resolve(audio))
          .catch(reject);
      });
    } catch (error) {
      console.error('Audio playback error:', error);
      throw error;
    }
  }
}

const sarvamService = new SarvamService();
export default sarvamService;