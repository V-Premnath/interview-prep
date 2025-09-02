import AudioStreamer from './AudioStreamer';
import { Headphones, Sparkles, Zap, Shield, Mic, Brain } from 'lucide-react';
import './app.css';

function App() {
  return (
    <div className="app-container">
      {/* Animated Background */}
      <div className="animated-bg-container">
        <div className="animated-bg-shape shape1"></div>
        <div className="animated-bg-shape shape2"></div>
        <div className="animated-bg-shape shape3"></div>
      </div>

      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo-container">
            <div className="logo-icon-wrapper">
              <div className="logo-icon">
                <Headphones />
              </div>
              <div className="logo-pulse-dot"></div>
            </div>
            <div>
              <h1 className="logo-title">VoiceFlow</h1>
              <p className="logo-subtitle">AI-Powered Transcription</p>
            </div>
          </div>

          <div className="status-indicator">
            <div className="status-dot"></div>
            <span className="status-text">Live & Ready</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Hero Section */}
        <div className="hero-section">
          <div className="hero-badge">
            <Sparkles />
            Next-Generation Speech Recognition
          </div>

          <h2 className="hero-title">
            Transform
            <span className="hero-title-gradient"> Speech to Text</span>
          </h2>

          <p className="hero-description">
            Experience the future of voice recognition with our cutting-edge AI technology.
            Speak naturally and watch your words materialize instantly with unprecedented accuracy.
          </p>
        </div>

        {/* Audio Streamer */}
        <div className="audio-streamer-wrapper">
          <AudioStreamer />
        </div>

        {/* Features Grid */}
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon-wrapper feature-icon-zap">
              <Zap />
            </div>
            <h3 className="feature-title">Lightning Speed</h3>
            <p className="feature-description">
              Real-time transcription with sub-second latency. Experience instant speech-to-text
              conversion that keeps up with your natural speaking pace.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper feature-icon-shield">
              <Shield />
            </div>
            <h3 className="feature-title">Privacy First</h3>
            <p className="feature-description">
              Your conversations stay private with end-to-end encryption and zero data retention.
              Advanced security protocols protect your sensitive information.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper feature-icon-brain">
              <Brain />
            </div>
            <h3 className="feature-title">AI Precision</h3>
            <p className="feature-description">
              Advanced neural networks trained on millions of hours of speech data deliver
              industry-leading accuracy across accents and languages.
            </p>
          </div>
        </div>

        {/* Getting Started */}
        <div className="getting-started-section">
          <div className="getting-started-header">
            <h3 className="getting-started-title">Ready to Get Started?</h3>
            <p className="getting-started-subtitle">
              Follow these simple steps to begin transcribing
            </p>
          </div>

          <div className="steps-grid">
            <div className="step">
              <div className="step-number step-number-1">1</div>
              <div>
                <h4 className="step-title">Grant Microphone Access</h4>
                <p className="step-description">
                  Click the record button and allow microphone permissions when prompted by your browser.
                </p>
              </div>
            </div>

            <div className="step">
              <div className="step-number step-number-2">2</div>
              <div>
                <h4 className="step-title">Start Speaking</h4>
                <p className="step-description">
                  Speak clearly and naturally. Watch as your words are transcribed with remarkable accuracy.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-logo">
            <div className="footer-logo-icon">
              <Headphones />
            </div>
            <div>
              <span className="footer-logo-title">VoiceFlow</span>
              <p className="footer-logo-subtitle">Powered by Advanced AI</p>
            </div>
          </div>

          <div className="footer-info">
            <div className="footer-info-item">
              <Mic />
              <span>Real-Time Processing</span>
            </div>
            <div className="footer-info-item">
              <Shield />
              <span>Enterprise Security</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
