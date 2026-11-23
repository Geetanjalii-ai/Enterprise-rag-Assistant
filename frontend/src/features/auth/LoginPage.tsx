import React from 'react';
import { LoginForm } from './LoginForm';
import { APP_NAME, BRAND_STRINGS } from '../../content/brand';
import { Sparkles } from 'lucide-react';

export const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen w-full bg-[var(--bg)] flex items-stretch">
      {/* Left panel - dark with radial glows (desktop only) */}
      <div className="hidden lg:flex w-[45%] m-4 rounded-2xl bg-[#0C0C0E] p-10 flex-col justify-between relative overflow-hidden text-white shadow-sm">
        {/* Blurred radial glows */}
        <div
          className="absolute -bottom-20 -left-20 w-[420px] h-[420px] rounded-full pointer-events-none filter blur-[90px] opacity-25"
          style={{ background: '#B7A9F0' }}
        />
        <div
          className="absolute -top-20 -right-20 w-[420px] h-[420px] rounded-full pointer-events-none filter blur-[90px] opacity-20"
          style={{ background: '#9CC7F0' }}
        />

        {/* Top brand header */}
        <div className="relative z-10 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center">
            <Sparkles size={18} strokeWidth={1.5} className="text-white" />
          </div>
          <span className="font-semibold text-[17px] tracking-tight">{APP_NAME}</span>
        </div>

        {/* Bottom headline & pills */}
        <div className="relative z-10 max-w-md">
          <h2 className="text-[36px] font-semibold leading-[42px] tracking-tight mb-4 text-white">
            {BRAND_STRINGS.login.headline}
          </h2>
          <p className="text-[14px] leading-[22px] text-white/70 mb-8 font-normal">
            {BRAND_STRINGS.login.paragraph}
          </p>

          <div className="flex flex-wrap gap-2">
            {BRAND_STRINGS.login.pills.map((pill) => (
              <span
                key={pill}
                className="px-3 py-1 rounded-full text-[12px] font-medium border border-white/20 bg-white/5 text-white/90 backdrop-blur-sm"
              >
                {pill}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel - form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <LoginForm />
      </div>
    </div>
  );
};
