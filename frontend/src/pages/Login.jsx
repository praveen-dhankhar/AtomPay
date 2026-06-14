import { useState } from "react";
import { api } from "../api";
import AtomLoader from "../components/AtomLoader";
import "../styles/auth.css";

export default function Login({ onLogin, goToSignup }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ email: "", password: "", otp: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const startCooldown = () => {
    setCooldown(60);
    const timer = setInterval(() => {
      setCooldown(c => {
        if (c <= 1) { clearInterval(timer); return 0; }
        return c - 1;
      });
    }, 1000);
  };

  const handleSendOTP = async () => {
    setError("");
    if (!form.email || !form.password)
      return setError("Enter your email and password");
    setLoading(true);
    try {
      await api("/auth/send-otp", {
        method: "POST",
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      setStep(2);
      startCooldown();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    setError("");
    if (!form.otp || form.otp.length !== 6)
      return setError("Enter the 6-digit OTP");
    setLoading(true);
    try {
      const data = await api("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email: form.email, otp: form.otp }),
      });
      onLogin(data.accessToken, data.refreshToken, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-orb auth-orb-1" />
      <div className="auth-orb auth-orb-2" />

      <div className="auth-card">
        <div className="auth-brand">
          <AtomLoader size={56} />
          <div className="auth-wordmark">
            Atom<span>Pay</span>
          </div>
        </div>

        <p className="auth-subtitle">
          {step === 1
            ? "Money, in motion."
            : `OTP sent to ${form.email}`}
        </p>

        {/* Step indicator */}
        <div className="auth-steps">
          {[1, 2].map(s => (
            <div key={s} className={`auth-step-bar ${step >= s ? "active" : ""}`} />
          ))}
        </div>

        <div className="auth-form">
          {step === 1 && (
            <>
              <div className="input-group">
                <label>Email</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                />
              </div>
              <div className="input-group">
                <label>Password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  onKeyDown={e => e.key === "Enter" && handleSendOTP()}
                />
              </div>

              {error && <div className="auth-error">{error}</div>}

              <button className="auth-btn" onClick={handleSendOTP} disabled={loading}>
                {loading ? <AtomLoader size={22} /> : "Send OTP →"}
              </button>
            </>
          )}

          {step === 2 && (
            <>
              <div className="input-group">
                <label>Email OTP (valid 60 seconds)</label>
                <input
                  className="otp-input"
                  type="text"
                  placeholder="••••••"
                  maxLength={6}
                  value={form.otp}
                  onChange={e => setForm({ ...form, otp: e.target.value.replace(/\D/g, "") })}
                  onKeyDown={e => e.key === "Enter" && handleVerifyOTP()}
                />
              </div>

              {error && <div className="auth-error">{error}</div>}

              <button className="auth-btn" onClick={handleVerifyOTP} disabled={loading}>
                {loading ? <AtomLoader size={22} /> : "Verify & Login ⚡"}
              </button>

              <button
                className="auth-btn ghost"
                onClick={handleSendOTP}
                disabled={cooldown > 0 || loading}
              >
                {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend OTP"}
              </button>

              <button
                className="auth-link-btn"
                onClick={() => { setStep(1); setError(""); setForm({ ...form, otp: "" }); }}
              >
                ← Change email
              </button>
            </>
          )}

          <p className="auth-switch">
            Don't have an account?{" "}
            <span onClick={goToSignup}>Sign up</span>
          </p>
        </div>
      </div>
    </div>
  );
}
