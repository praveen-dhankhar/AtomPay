import { useState } from "react";
import { api } from "../api";
import "../styles/auth.css";

export default function Signup({ onLogin, goToLogin }) {
  const [form, setForm] = useState({ name: "", email: "", username: "", password: "", pin: "", otp: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [otpSent, setOtpSent] = useState(false);

  const handleSendOTP = async () => {
    setError("");
    if (!form.name || !form.email || !form.username || !form.password || !form.pin)
      return setError("Fill all fields");
    if (form.pin.length !== 6 || !/^\d{6}$/.test(form.pin))
      return setError("PIN must be exactly 6 digits");
    if (form.password.length < 8)
      return setError("Password must be at least 8 characters");

    setLoading(true);
    try {
      await api("/auth/send-signup-otp", {
        method: "POST",
        body: JSON.stringify({ email: form.email }),
      });
      setOtpSent(true);
    } catch (err) {
      setError(err.message || "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setError("");
    if (form.otp.length !== 6 || !/^\d{6}$/.test(form.otp))
      return setError("OTP must be exactly 6 digits");

    setLoading(true);
    try {
      const data = await api("/auth/signup", {
        method: "POST",
        body: JSON.stringify(form),
      });
      onLogin(data.accessToken, data.refreshToken, data.user);
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const f = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  return (
    <div className="auth-container">
      <div className="auth-bg-glow" />
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-atom">⚡</span>
          <span className="logo-text">AtomPay</span>
        </div>
        <p className="auth-subtitle">₹500,000 signup bonus ke saath shuru karo</p>

        <div className="auth-form">
          {!otpSent ? (
            <>
              {[
                { key: "name", label: "Full Name", placeholder: "Akshy Dhankhar", type: "text" },
                { key: "email", label: "Email", placeholder: "you@example.com", type: "email" },
                { key: "username", label: "Username", placeholder: "akshy123", type: "text" },
                { key: "password", label: "Password", placeholder: "Min 8 characters", type: "password" },
                { key: "pin", label: "UPI PIN (6 digits)", placeholder: "••••••", type: "password" },
              ].map(({ key, label, placeholder, type }) => (
                <div className="input-group" key={key}>
                  <label>{label}</label>
                  <input
                    type={type}
                    placeholder={placeholder}
                    value={form[key]}
                    onChange={f(key)}
                    maxLength={key === "pin" ? 6 : undefined}
                  />
                </div>
              ))}

              {error && <div className="auth-error">{error}</div>}

              <button className="auth-btn" onClick={handleSendOTP} disabled={loading}>
                {loading ? <span className="spinner" /> : "Send OTP"}
              </button>
            </>
          ) : (
            <>
              <div className="input-group">
                <label>Enter OTP Code</label>
                <input
                  type="text"
                  placeholder="6 digit OTP from your email"
                  value={form.otp}
                  onChange={f("otp")}
                  maxLength={6}
                />
              </div>

              {error && <div className="auth-error">{error}</div>}

              <button className="auth-btn" onClick={handleSubmit} disabled={loading}>
                {loading ? <span className="spinner" /> : "Create Account"}
              </button>
            </>
          )}

          <p className="auth-switch">
            Already account hai?{" "}
            <span onClick={goToLogin}>Login karo</span>
          </p>
        </div>
      </div>
    </div>
  );
}
