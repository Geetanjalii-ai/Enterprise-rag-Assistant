import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Checkbox } from '../../components/ui/Checkbox';
import { BRAND_STRINGS } from '../../content/brand';
import { Eye, EyeOff, HelpCircle } from 'lucide-react';

export const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showHelpPopover, setShowHelpPopover] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }

    setIsLoading(true);
    try {
      await login(email, password, remember);
      navigate('/chat');
    } catch (err: any) {
      if (err.response?.status === 429) {
        setError(BRAND_STRINGS.login.lockoutMessage);
      } else {
        setError(BRAND_STRINGS.login.errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[360px] mx-auto">
      <div className="mb-6">
        <h1 className="text-[24px] font-semibold text-[var(--text)] tracking-tight">
          {BRAND_STRINGS.login.title}
        </h1>
        <p className="text-[14px] text-[var(--text-muted)] mt-1">
          {BRAND_STRINGS.login.subtitle}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-[var(--pastel-rose-bg)] border border-[var(--pastel-rose-text)]/20 rounded-lg text-[13px] text-[var(--pastel-rose-text)]">
            {error}
          </div>
        )}

        <Input
          label="Email address"
          type="email"
          name="email"
          autoComplete="email"
          placeholder="name@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <div className="relative">
          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            name="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-[34px] text-[var(--text-subtle)] hover:text-[var(--text)] transition-colors"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>

        <div className="flex items-center justify-between pt-1">
          <Checkbox
            label="Keep me signed in"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
          />

          <div className="relative">
            <button
              type="button"
              onClick={() => setShowHelpPopover(!showHelpPopover)}
              className="text-[13px] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors inline-flex items-center gap-1"
            >
              Forgot password?
            </button>

            {showHelpPopover && (
              <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-[0_8px_24px_rgba(15,17,21,0.08)] text-[12px] text-[var(--text-muted)] z-50">
                <div className="flex items-start gap-2">
                  <HelpCircle size={16} className="text-[var(--text-subtle)] shrink-0 mt-0.5" />
                  <div>{BRAND_STRINGS.login.forgotPasswordPopover}</div>
                </div>
              </div>
            )}
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          className="w-full mt-2"
          isLoading={isLoading}
        >
          {BRAND_STRINGS.login.submitButton}
        </Button>

        <p className="text-[12px] text-center text-[var(--text-subtle)] mt-4">
          {BRAND_STRINGS.login.caption}
        </p>
      </form>
    </div>
  );
};
