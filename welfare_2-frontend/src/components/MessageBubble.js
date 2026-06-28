import React from 'react';
import './MessageBubble.css';

function formatTime(d) { return new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }

const questionMarkIcon = `data:image/svg+xml,${encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="45" fill="url(#grad)" />
    <defs>
      <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#6366f1;stop-opacity:1" />
      </linearGradient>
    </defs>
    <text x="50" y="65" font-size="50" font-weight="bold" fill="white" text-anchor="middle" font-family="Arial">?</text>
  </svg>
`)}`;

export default function MessageBubble({ message }) {
  const isBot = message.role === 'bot';
  return (
    <div className='msg-row'>
      {isBot && <div className='msg-avatar'><img src={questionMarkIcon} alt="Bot" /></div>}
      <div className='msg-bubble'>
        <div className='msg-text'>{message.text}</div>
        <div className='msg-time'>{formatTime(message.timestamp)}</div>
      </div>
    </div>
  );
}
