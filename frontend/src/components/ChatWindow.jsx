import React, { useRef, useEffect } from 'react';
import { Bot, User } from 'lucide-react';

const ChatWindow = ({ messages, isTyping }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-zinc-950">
      {messages.filter(m => m.role !== 'system').map((msg, idx) => {
        const isAI = msg.role === 'assistant';
        return (
          <div key={idx} className={`flex ${isAI ? 'justify-start' : 'justify-end'}`}>
            <div className={`flex gap-4 max-w-[80%] ${isAI ? 'flex-row' : 'flex-row-reverse'}`}>
              
              <div className={`p-2 h-10 w-10 flex-shrink-0 flex items-center justify-center rounded-xl bg-zinc-900 border ${isAI ? 'border-zinc-800' : 'border-[#6C63FF]/30'}`}>
                 {isAI ? <Bot className="text-emerald-400 w-5 h-5" /> : <User className="text-[#6C63FF] w-5 h-5" />}
              </div>
              
              <div className={`p-4 rounded-2xl ${isAI ? 'bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-tl-sm' : 'bg-[#6C63FF] text-white rounded-tr-sm shadow-lg shadow-[#6C63FF]/20'}`}>
                 <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                 <span className={`text-[10px] mt-2 block opacity-50 ${isAI ? 'text-zinc-500' : 'text-white/80 text-right'}`}>
                   {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                 </span>
              </div>
            </div>
          </div>
        );
      })}

      {isTyping && (
         <div className="flex justify-start">
            <div className="flex gap-4 max-w-[80%]">
              <div className="p-2 h-10 w-10 flex items-center justify-center rounded-xl bg-zinc-900 border border-zinc-800">
                 <Bot className="text-emerald-400 w-5 h-5" />
              </div>
              <div className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-tl-sm flex items-center gap-2">
                 <span className="w-2 h-2 bg-emerald-400/50 rounded-full animate-bounce"></span>
                 <span className="w-2 h-2 bg-emerald-400/50 rounded-full animate-bounce" style={{animationDelay: "0.2s"}}></span>
                 <span className="w-2 h-2 bg-emerald-400/50 rounded-full animate-bounce" style={{animationDelay: "0.4s"}}></span>
              </div>
            </div>
         </div>
      )}
      
      <div ref={bottomRef} />
    </div>
  );
};

export default ChatWindow;
