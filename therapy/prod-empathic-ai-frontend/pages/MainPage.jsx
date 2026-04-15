"use client";

import React, { useState } from 'react';
import AudioBubble from '../components/AudioBubble.jsx';

function MainPage() {
  const [messages, setMessages] = useState([
    { text: "yes u doing good blud", sender: "ai", date: "Feb 17" }
  ]);
  const [inputText, setInputText] = useState("");

  const sendMessage = () => {
    if (inputText.trim()) {
      setMessages([...messages, { text: inputText, sender: "user", date: "Feb 17" }]);
      setInputText("");
    }
  };

  return (
    <div className="flex h-screen bg-[#E8F5E9]">
      {/* Left Sidebar - Calendar/Dates */}
      <div className="w-32 bg-[#81C784] flex flex-col">
        {["Feb 17", "Feb 16", "Feb 15", "Feb 14", "Feb 13", "Feb 12", "Feb 11", "Feb 10"].map((date, idx) => (
          <div 
            key={date}
            className={`p-4 text-sm font-medium border-b border-[#66BB6A] cursor-pointer hover:bg-[#66BB6A] transition-colors
              ${idx === 0 ? 'bg-[#A5D6A7]' : 'bg-[#81C784]'}`}
          >
            {date}
          </div>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col p-8">
        {/* Top Section - Audio Bubble + Chat */}
        <div className="flex gap-6 mb-6 flex-1">
          {/* Audio Bubble */}
          <div className="flex-1 bg-[#C8E6C9] rounded-3xl p-6 flex items-center justify-center">
            <div className="w-full h-full">
              <AudioBubble />
            </div>
          </div>

          {/* Chat Messages + Plant */}
          <div className="w-96 flex flex-col">
            <div className="flex-1 bg-[#C8E6C9] rounded-3xl p-6 mb-4 overflow-y-auto">
              {messages.map((msg, idx) => (
                <div key={idx} className={`mb-4 ${msg.sender === 'ai' ? 'flex justify-start' : 'flex justify-end'}`}>
                  <div className={`max-w-xs p-4 rounded-2xl ${
                    msg.sender === 'ai' 
                      ? 'bg-white text-gray-800' 
                      : 'bg-[#66BB6A] text-white'
                  }`}>
                    <p className="text-sm">{msg.text}</p>
                  </div>
                </div>
              ))}
            </div>
            {/* Plant decoration */}
            <div className="text-6xl text-center">
              🌱
            </div>
          </div>
        </div>

        {/* Bottom Input Area */}
        <div className="bg-[#4CAF50] rounded-3xl p-6">
          <div className="flex gap-4 items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 bg-[#F1F8E9] rounded-full px-6 py-4 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#66BB6A]"
            />
            <button
              onClick={sendMessage}
              className="bg-[#66BB6A] hover:bg-[#81C784] text-white px-8 py-4 rounded-full font-medium transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MainPage;