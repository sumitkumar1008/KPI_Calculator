import { useState } from "react";
import "./login.css";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();

    console.log("Email:", email);
    console.log("Password:", password);

    onLogin();

    // Backend login/API will be connected here later.
  };

  return (
    <div className="login-page">
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
          <h1>Welcome Back</h1>
          <p>Please login to your account</p>
        </div>

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
              onChange={(event) => setEmail(event.target.value)}
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
                onChange={(event) => setPassword(event.target.value)}
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
  );
}

export default Login;
