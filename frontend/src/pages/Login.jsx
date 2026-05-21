import { useState } from "react";
import { api } from "../api";
import "../styles/auth.css";

export default function Login({ onLogin, goToSignup }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
      email: "", password: "", otp: ""
  });
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
      return setError("Email aur password daalo");
    setLoading(true);
    try {
      await api("/auth/send-otp", {
        method: "POST",
        body: JSON.stringify({
            email: form.email,
            password: form.password
        }),
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
      return setError("6-digit OTP daalo");
    setLoading(true);
    try {
      const data = await api("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({
            email: form.email,
            otp: form.otp
        }),
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
      <div className="auth-bg-glow" />
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-atom">⚡</span>
          <span className="logo-text">AtomPay</span>
        </div>
        <p className="auth-subtitle">
          {step === 1
            ? "India ka naya payment wallet"
            : `OTP bheja gaya — ${form.email}`}
        </p>

        {/* Step indicator */}
        <div style={{
            display: "flex", gap: 8,
            marginBottom: 24
        }}>
          {[1, 2].map(s => (
            <div key={s} style={{
              height: 3,
              flex: 1,
              borderRadius: 100,
              background: step >= s
                ? "#FF5722"
                : "#222",
              transition: "background 0.3s"
            }} />
          ))}
        </div>

        <div className="auth-form">
          {step === 1 && (
            <>
              <div className="input-group">
                <label>Email</label>
                <input
                  type="email"
                  placeholder="akshay@example.com"
                  value={form.email}
                  onChange={e => setForm({
                      ...form, email: e.target.value
                  })}
                />
              </div>
              <div className="input-group">
                <label>Password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm({
                      ...form, password: e.target.value
                  })}
                  onKeyDown={e =>
                      e.key === "Enter" && handleSendOTP()
                  }
                />
              </div>

              {error && (
                  <div className="auth-error">{error}</div>
              )}

              <button
                className="auth-btn"
                onClick={handleSendOTP}
                disabled={loading}
              >
                {loading
                    ? <span className="spinner" />
                    : "Send OTP →"}
              </button>
            </>
          )}

          {step === 2 && (
            <>
              <div className="input-group">
                <label>Email OTP (60 seconds valid)</label>
                <input
                  type="text"
                  placeholder="6-digit OTP"
                  maxLength={6}
                  value={form.otp}
                  onChange={e => setForm({
                      ...form,
                      otp: e.target.value.replace(/\D/g, "")
                  })}
                  onKeyDown={e =>
                      e.key === "Enter" && handleVerifyOTP()
                  }
                  style={{
                      fontSize: 24,
                      letterSpacing: 8,
                      textAlign: "center"
                  }}
                />
              </div>

              {error && (
                  <div className="auth-error">{error}</div>
              )}

              <button
                className="auth-btn"
                onClick={handleVerifyOTP}
                disabled={loading}
              >
                {loading
                    ? <span className="spinner" />
                    : "Verify & Login ⚡"}
              </button>

              <button
                className="auth-btn"
                onClick={handleSendOTP}
                disabled={cooldown > 0 || loading}
                style={{
                    marginTop: 8,
                    background: "transparent",
                    border: "1.5px solid #FF5722",
                    color: cooldown > 0 ? "#555" : "#FF5722",
                    borderColor: cooldown > 0
                        ? "#333"
                        : "#FF5722"
                }}
              >
                {cooldown > 0
                    ? `Resend in ${cooldown}s`
                    : "Resend OTP"}
              </button>

              <button
                style={{
                    background: "none",
                    border: "none",
                    color: "#666",
                    cursor: "pointer",
                    marginTop: 8,
                    fontSize: 13
                }}
                onClick={() => {
                    setStep(1);
                    setError("");
                    setForm({ ...form, otp: "" });
                }}
              >
                ← Email change karo
              </button>
            </>
          )}

          <p className="auth-switch">
            Account nahi hai?{" "}
            <span onClick={goToSignup}>Sign up karo</span>
          </p>
        </div>
      </div>
    </div>
  );
}
