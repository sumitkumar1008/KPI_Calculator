import { useState } from "react";
import Footer from "./Footer";
import "./login.css";

const VALID_EMAIL = "airtelcenter@gmail.com";
const VALID_PASSWORD = "Airtel@center123";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    setErrorMessage("");

    const normalizedEmail = email.trim().toLowerCase();

    if (normalizedEmail !== VALID_EMAIL.toLowerCase()) {
      setErrorMessage("Wrong email id");
      return;
    }

    if (password !== VALID_PASSWORD) {
      setErrorMessage("Incorrect password");
      return;
    }

    onLogin();
  };

  return (
    <div className="login-page">
      <div className="login-card-container">
        <div className="login-card">
        {/* Airtel Logo */}
        <div className="company-logo">
          <img
            src="https://res.cloudinary.com/t5lye7wm/image/upload/v1787722271/airtel_logo_project-removebg-preview.png"
            alt="Airtel Logo"
          />
        </div>

        {/* Heading */}
        <div className="login-header">
          <h1>KPI Calculator</h1>
          <p>Please login to your account</p>
        </div>

        {/* Error Alert Banner */}
        {errorMessage && (
          <div className="login-error-alert" role="alert">
            <span className="login-error-icon">⚠️</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="login-form">
          {/* Email */}
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              placeholder="Enter your email"
              value={email}
              className={errorMessage && errorMessage.includes("email") ? "input-error" : ""}
              onChange={(event) => {
                setEmail(event.target.value);
                if (errorMessage) setErrorMessage("");
              }}
              required
            />
          </div>

          {/* Password */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-container">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                className={errorMessage && errorMessage.includes("password") ? "input-error" : ""}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (errorMessage) setErrorMessage("");
                }}
                required
              />
              <button
                type="button"
                className="show-password"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Remember Me / Forgot Password */}
          <div className="login-options">
            <label className="remember-me">
              <input type="checkbox" />
              <span>Remember me</span>
            </label>
            <button
              type="button"
              className="forgot-password"
              onClick={() => console.log("Forgot password clicked")}
            >
              Forgot Password?
            </button>
          </div>

          {/* Login Button */}
          <button type="submit" className="login-button">
            Login
          </button>
        </form>
      </div>
      </div>
      <Footer />
    </div>
  );
}

export default Login;
