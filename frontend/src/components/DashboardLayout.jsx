import React, { useState, useEffect, useRef } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import logo from "../assets/logo.png";
import profile from "../assets/profile.png";
import "../styles/Dashboard.css";

const DashboardLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dropdownRef = useRef(null);

  const [userEmail, setUserEmail] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    fetch("http://localhost:8000/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Unauthorized");
        return res.json();
      })
      .then((data) => setUserEmail(data.email))
      .catch(() => navigate("/login"));
  }, [navigate]);

  // close dropdown if clicked outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login", { replace: true });
  };

  const handleNavClick = (path) => navigate(path);

  const isActive = (path) =>
    location.pathname === path ||
    (path === "/dashboard" && location.pathname === "/");

  return (
    <div className="dashboard-container">
      <div className="navbar">
        <div className="logo-img">
          <img src={logo} alt="Secure AI Vault Logo" />
        </div>
        <div className="navlist">
          <ul>
            <li
              className={isActive("/dashboard") ? "active" : ""}
              onClick={() => handleNavClick("/dashboard")}
            >
              Dashboard
            </li>
            <li
              className={isActive("/upload") ? "active" : ""}
              onClick={() => handleNavClick("/upload")}
            >
              Upload
            </li>
            <li
              className={isActive("/analytics") ? "active" : ""}
              onClick={() => handleNavClick("/analytics")}
            >
              Analytics
            </li>
            <li
              className={isActive("/documents") ? "active" : ""}
              onClick={() => handleNavClick("/documents")}
            >
              Documents
            </li>
            <li
              className={isActive("/history") ? "active" : ""}
              onClick={() => handleNavClick("/history")}
            >
              History
            </li>
          </ul>
        </div>
        <div className="profile-section" ref={dropdownRef}>
          <button className="profile-btn" onClick={() => setShowDropdown(!showDropdown)}>
            <img src={profile} alt="Profile" />
          </button>
          {showDropdown && (
            <div className="profile-dropdown">
              <ul>
                <li>
                  <Link>{userEmail || "User"}</Link>
                </li>
                <li>
                  <Link to="/profile">User Profile</Link>
                </li>
                <li>
                  <button onClick={handleLogout}>Logout</button>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* 👇 This renders the child page inside the layout */}
      <div className="dashboard-content">
        <Outlet />
      </div>
    </div>
  );
};

export default DashboardLayout;
